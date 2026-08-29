"""提取任务接口：提交 / 查询进度 / 手动文案重试 / 音频上传。对齐 docs/API.md §3.1。"""
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db, SessionLocal
from app.models import Capsule, ExtractionTask, User, Video, task_public_id
from app.models.video import source_digest
from app.schemas.extraction import ExtractionCreate, ManualRetry
from app.schemas.response import ERR_NOT_FOUND, ERR_PARAM, ERR_SHARE_UNRESOLVABLE, biz_error, ok
from app.workers.extraction_runner import run_extraction

router = APIRouter(prefix="/extractions", tags=["extractions"])

MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 16k 单声道 wav 约 32KB/s，20MB ≈ 10 分钟


@router.post("")
def create_extraction(
    body: ExtractionCreate,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        mode = body.mode()
    except ValueError as exc:
        raise biz_error(ERR_PARAM, str(exc)) from exc

    if mode == "manual":
        # manual 同样按文案内容幂等（source_hash=文案摘要）
        video = (
            db.query(Video)
            .filter(Video.user_id == user.id, Video.source_hash == source_digest(body.manual_text))
            .first()
        )
        if video is None:
            video = Video(
                user_id=user.id,
                platform="manual",
                source_url=None,
                source_hash=source_digest(body.manual_text),
                title=body.title or "手动粘贴文案",
                # 手动文案即转写结果，直接入库，runner 跳过转写步
                transcript=body.manual_text,
                transcript_source="manual",
            )
            db.add(video)
            db.flush()
    else:
        # 幂等：同一用户同一来源已有进行中/最近任务则直接返回（TC-B05）
        video = (
            db.query(Video)
            .filter(
                Video.user_id == user.id,
                Video.source_hash == source_digest(_extract_url(body.share_text)),
            )
            .first()
        )
        if video is None:
            video = Video(
                user_id=user.id,
                platform="bilibili",  # resolver 确认平台后 runner 内修正
                source_url=_extract_url(body.share_text),
                source_hash=source_digest(_extract_url(body.share_text)),
                title=body.share_text[:200],
            )
            db.add(video)
            db.flush()

    # 幂等（API.md §1 / 第七轮审查 2.1）：同视频已有进行中任务直接返回该任务，
    # 避免重复跑 LLM（顺序提交）和唯一约束冲突（并发提交）
    in_progress = (
        db.query(ExtractionTask)
        .filter(
            ExtractionTask.video_id == video.id,
            ExtractionTask.status.in_(["pending", "resolving", "transcribing", "extracting"]),
        )
        .order_by(ExtractionTask.id.desc())
        .first()
    )
    if in_progress:
        return ok(
            {
                "task_id": task_public_id(in_progress.id, in_progress.created_at),
                "status": in_progress.status,
                "video_id": video.id,
            }
        )

    task = ExtractionTask(video_id=video.id, user_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)

    background.add_task(run_extraction, SessionLocal, task.id)
    return ok(
        {
            "task_id": task_public_id(task.id, task.created_at),
            "status": task.status,
            "video_id": video.id,
        }
    )


@router.post("/audio")
def create_audio_extraction(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """T3.7 音频捕获通道：App 采集的正在播放音频（wav）上传 → ASR 转写 → 胶囊。"""
    import threading

    data = file.file.read()
    if len(data) < 1024:
        raise biz_error(ERR_PARAM, "音频内容过短")
    if len(data) > MAX_AUDIO_BYTES:
        raise biz_error(ERR_PARAM, "音频超过 10 分钟上限")

    wav_path = Path(tempfile.gettempdir()) / f"yhsg_cap_{uuid.uuid4().hex}.wav"
    wav_path.write_bytes(data)

    video = Video(
        user_id=user.id,
        platform="capture",
        source_url=None,
        source_hash=source_digest(f"capture:{wav_path.name}"),
        title="音频捕获片段",
    )
    db.add(video)
    db.flush()
    task = ExtractionTask(video_id=video.id, user_id=user.id, status="transcribing")
    db.add(task)
    db.commit()
    db.refresh(task)

    def _asr_then_extract() -> None:
        """先转写（模型推理，CPU 数秒到数十秒），转写文本落库后复用提取状态机。"""
        from app.services.transcript.asr_funasr import transcribe_file
        from app.workers.extraction_runner import _set_status

        s: Session = SessionLocal()
        try:
            v = s.get(Video, video.id)
            t = s.get(ExtractionTask, task.id)
            try:
                v.transcript = transcribe_file(wav_path)
                v.transcript_source = "asr"
                s.commit()
            except Exception as exc:  # noqa: BLE001
                _set_status(s, t, "failed", f"ASR: {exc}"[:512])
                return
            if not (v.transcript or "").strip():
                # 静音/无媒体音：必须在此拦截，否则 runner 会对无 URL 的 capture
                # 视频再走一次 URL 转写链，报出无关的"手动粘贴文案"错误（实测踩坑）
                _set_status(s, t, "failed", "未捕获到有效语音：确认目标 App 正在播放媒体音（建议外放）")
                return
            run_extraction(SessionLocal, task.id)
        finally:
            s.close()
            wav_path.unlink(missing_ok=True)

    threading.Thread(target=_asr_then_extract, daemon=True).start()
    return ok(
        {
            "task_id": task_public_id(task.id, task.created_at),
            "status": task.status,
            "video_id": video.id,
        }
    )


def _extract_url(share_text: str) -> str:
    from app.services.resolver import extract_first_url

    url = extract_first_url(share_text or "")
    if not url:
        # 口令无法解析 = 2001（API.md 错误表/TC-B04），而非参数错误
        raise biz_error(ERR_SHARE_UNRESOLVABLE, "share_text 中未找到可识别的视频链接")
    return url


@router.get("/{task_id}")
def get_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = _find_task(task_id, user, db)
    return ok(
        {
            "task_id": task_id,
            "status": task.status,
            "stage_error": task.stage_error,
            "capsule_id": _capsule_id_of(db, task),
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
    )


@router.post("/{task_id}/manual-text")
def retry_with_manual_text(
    task_id: str,
    body: ManualRetry,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """failed → transcribing：手动粘贴文案重试（状态机见 PRD §6.2）。"""
    task = _find_task(task_id, user, db)
    if task.status != "failed":
        raise biz_error(ERR_PARAM, "仅 failed 状态任务可手动重试")

    video = db.get(Video, task.video_id)
    video.transcript = body.manual_text
    video.transcript_source = "manual"
    task.status = "transcribing"
    task.stage_error = None
    db.commit()

    background.add_task(run_extraction, SessionLocal, task.id)
    return ok({"task_id": task_id, "status": task.status, "video_id": video.id})


def _find_task(task_id: str, user: User, db: Session) -> ExtractionTask:
    """task_id 格式 {ts}_{id}；越权/不存在一律 404 防探测（API.md §4）。"""
    try:
        real_id = int(task_id.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        raise biz_error(ERR_NOT_FOUND, "task not found") from None
    task = db.get(ExtractionTask, real_id)
    if task is None or task.user_id != user.id:
        raise biz_error(ERR_NOT_FOUND, "task not found")
    return task


def _capsule_id_of(db: Session, task: ExtractionTask) -> int | None:
    capsule = db.query(Capsule).filter(Capsule.video_id == task.video_id).first()
    return capsule.id if capsule else None
