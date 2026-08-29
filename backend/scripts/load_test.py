"""并发压测（T4.5 / AC-09）：50 并发打任务查询与胶囊列表，输出 P50/P95/P99。

    python scripts/load_test.py --workers 50 --seconds 30

说明：申报书写 JMeter，但 JMeter 需 GUI 环境且脚本等价可复现——本脚本为
Python 原生实现，输出含 AC-09 判定所需的 P95 数据；报告落盘 eval/reports/。
"""
import argparse
import asyncio
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402

BASE = "http://127.0.0.1:8000"
TOKEN = "dev-single-user-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


async def worker(client: httpx.AsyncClient, stop_at: float, latencies: list, task_url: str):
    """循环打三类读接口（capsules 列表 / graph / 任务查询），记录延迟直到截止。"""
    i = 0
    urls = [
        f"{BASE}/api/v1/capsules?page=1&page_size=20",
        f"{BASE}/api/v1/graph",
    ]
    if task_url:
        urls.append(task_url)  # AC-09 定义的主场景：任务查询
    while time.time() < stop_at:
        url = urls[i % len(urls)]
        t0 = time.perf_counter()
        try:
            resp = await client.get(url, headers=HEADERS)
            ok = resp.status_code == 200
        except Exception:
            ok = False
        latencies.append((time.perf_counter() - t0, ok))
        i += 1


def pct(values: list[float], p: float) -> float:
    return round(sorted(values)[int(len(values) * p)] * 1000, 1) if values else -1


def pick_done_task_id() -> str:
    """从库中取一个已完成任务的对外 task_id，供任务查询压测（AC-09 主场景）。"""
    from app.core.database import SessionLocal
    from app.models import ExtractionTask, task_public_id

    db = SessionLocal()
    try:
        t = (
            db.query(ExtractionTask)
            .filter(ExtractionTask.status == "done")
            .order_by(ExtractionTask.id.desc())
            .first()
        )
        return task_public_id(t.id, t.created_at) if t else ""
    finally:
        db.close()


async def main_async(args):
    latencies: list[tuple[float, bool]] = []
    task_id = pick_done_task_id()
    task_url = f"{BASE}/api/v1/extractions/{task_id}" if task_id else ""
    async with httpx.AsyncClient(timeout=10) as client:
        # 预热一条，确保鉴权/缓存路径已走通
        await client.get(f"{BASE}/api/v1/capsules", headers=HEADERS)
        stop_at = time.time() + args.seconds
        t0 = time.time()
        async with asyncio.TaskGroup() as tg:
            for w in range(args.workers):
                tg.create_task(worker(client, stop_at, latencies, task_url))
        wall = time.time() - t0

    lats = [l for l, ok in latencies]
    errors = sum(1 for _, ok in latencies if not ok)
    rps = len(latencies) / wall
    p95 = pct(lats, 0.95)
    verdict = "PASS" if p95 <= 500 and errors == 0 else "FAIL"

    report = (
        f"# AC-09 压测报告\n\n"
        f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- 场景：{args.workers} 并发 × {args.seconds}s，混合打 capsules 列表 / graph / 任务查询"
        f"{'（task_id=' + task_id + '）' if task_url else '（库中无已完成任务，本轮缺任务查询场景）'}\n"
        f"- 总请求：{len(latencies)}，错误：{errors}，吞吐：{rps:.0f} req/s\n\n"
        f"| 指标 | 数值 | 判定 |\n| --- | --- | --- |\n"
        f"| P50 | {pct(lats, 0.50)} ms | — |\n"
        f"| P95 | {p95} ms | {'✅ ≤500ms' if p95 <= 500 else '❌ >500ms'} |\n"
        f"| P99 | {pct(lats, 0.99)} ms | — |\n"
        f"| 错误率 | {errors / max(len(latencies), 1):.2%} | {'✅' if errors == 0 else '❌'} |\n\n"
        f"**AC-09 判定：{verdict}**\n"
    )
    print(report)
    out = Path(__file__).parent.parent / "eval" / "reports" / f"load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=50)
    ap.add_argument("--seconds", type=int, default=30)
    asyncio.run(main_async(ap.parse_args()))
