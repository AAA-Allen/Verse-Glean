"""提取任务状态机执行器（PRD B6）：pending → resolving → transcribing → extracting → done/failed。

MVP 用 FastAPI BackgroundTasks 同进程执行；M4 引 Redis/Celery 时本文件的状态迁移逻辑可整体复用。
"""
import asyncio
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Capsule, CapsuleTag, ExtractionTask, Video
from app.services import embedder, extractor, graph, resolver
from app.services.extractor import ExtractionError
from app.services.transcript.pipeline import TranscriptUnavailable, transcribe

# 中间态超时阈值：服务重启自愈（DATABASE.md §4）
STALE_AFTER = timedelta(minutes=10)


def _set_status(db: Session, task: ExtractionTask, status: str, error: str | None = None) -> None:
    task.status = status
    task.stage_error = error
    db.commit()
    logger.info("task {} -> {} {}", task.id, status, error or "")


def run_extraction(session_factory: sessionmaker, task_id: int) -> None:
    """同步执行全链路；任何异常收敛为 failed + stage_error，绝不向上抛。"""
    db: Session = session_factory()
    try:
        task = db.get(ExtractionTask, task_id)
        video = db.get(Video, task.video_id)
        try:
            # resolving：manual 模式无链接可解析，直接过
            _set_status(db, task, "resolving")
            if video.platform != "manual" and not video.transcript:
                resolved = await_(_resolve(video))
                # 平台/BV号以解析结果为准（创建时硬编码 bilibili，见 extractions.create）
                video.platform = resolved.platform
                video.bvid = resolved.bvid or video.bvid
                video.title = video.title or resolved.title
                video.cover_url = video.cover_url or resolved.cover_url
                video.duration_sec = video.duration_sec or resolved.duration_sec
                db.commit()

            # transcribing：已有转写（手动文案重试）则跳过
            _set_status(db, task, "transcribing")
            if not video.transcript:
                result = await_(_transcribe(video))
                video.transcript = result.text
                video.transcript_source = result.source
                db.commit()

            # extracting：LLM 提取 + pydantic 校验重试（extractor 内部处理）
            _set_status(db, task, "extracting")
            capsule_data, prompt_version = await_(_extract(video.transcript or ""))

            # 事务落库：任务 done + 胶囊 upsert + 标签重写（DATABASE.md §4 事务边界）
            capsule = db.query(Capsule).filter(Capsule.video_id == video.id).first()
            if capsule is None:
                capsule = Capsule(video_id=video.id, user_id=video.user_id)
                db.add(capsule)
            capsule.theme = capsule_data.theme
            capsule.variables = capsule_data.variables
            capsule.steps = capsule_data.steps
            capsule.tags = capsule_data.tags
            capsule.category = capsule_data.category
            capsule.model = get_settings().llm_model
            capsule.prompt_version = prompt_version
            db.flush()

            db.query(CapsuleTag).filter(CapsuleTag.capsule_id == capsule.id).delete()
            for tag in set(capsule_data.tags):
                db.add(CapsuleTag(capsule_id=capsule.id, tag=tag))
            task.raw_llm_output = None
            _set_status(db, task, "done")

            # 后置：向量化 + 语义建边（失败不回滚主流程，图谱 60s 内可见即可）
            _post_process(session_factory, capsule.id)
        except Exception as exc:  # noqa: BLE001 降级链要求任何单点失败收敛为 failed
            db.rollback()
            task = db.get(ExtractionTask, task_id)
            _set_status(db, task, "failed", f"{type(exc).__name__}: {exc}"[:512])
    finally:
        db.close()


# —— 异步服务的同步包装：BackgroundTasks 在线程池中调用，事件循环线程内运行 ——

async def _resolve(video: Video):
    return await resolver.resolve(video.source_url or "")


async def _transcribe(video: Video):
    return await transcribe(video.platform, video.source_url or "", video.bvid)


async def _extract(text: str):
    return await extractor.extract(text)


def await_(coro):
    """线程池内无运行中事件循环，安全地驱动协程到完成。"""
    return asyncio.run(coro)


def _post_process(session_factory: sessionmaker, capsule_id: int) -> None:
    """向量化+建边：使用独立会话，与已提交的主事务隔离，失败只告警。"""

    async def _job() -> None:
        db: Session = session_factory()
        try:
            capsule = db.get(Capsule, capsule_id)
            if capsule and await embedder.embed_capsule(db, capsule):
                graph.rebuild_links_for(db, capsule)
        finally:
            db.close()

    try:
        asyncio.run(_job())
    except Exception as exc:  # noqa: BLE001
        logger.error("post-process (embed/link) failed: {}", exc)


def recover_stale_tasks(session_factory: sessionmaker) -> int:
    """服务重启自愈：中间态超过 10 分钟的任务置 failed（可手动重试）。"""
    db: Session = session_factory()
    try:
        cutoff = datetime.now() - STALE_AFTER
        stale = db.scalars(
            select(ExtractionTask).where(
                ExtractionTask.status.in_(["resolving", "transcribing", "extracting"]),
                ExtractionTask.updated_at < cutoff,
            )
        ).all()
        for task in stale:
            _set_status(db, task, "failed", "interrupted: server restarted")
        return len(stale)
    finally:
        db.close()
