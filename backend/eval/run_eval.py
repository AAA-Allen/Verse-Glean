"""Prompt 质量评测（T4.1/T4.2，AC-03）：

    python eval/run_eval.py                 # 全量
    python eval/run_eval.py --limit 10      # 抽样
    python eval/run_eval.py --subset 装机配置

指标：提取成功率 / JSON 合法率（pydantic 通过即合法）/ 字段召回率（关键词命中）/
步骤数达标率 / 平均耗时。报告按 垂类 × prompt_version 聚合，落盘 eval/reports/。

数据集：eval/dataset.jsonl，每行 {"id","subset","category","text","expect"}。
扩充指引：目标 5 子集 × 40 条 = 200 条（DEVELOPMENT_PLAN T4.1），
来源取公开短视频转写文案（人工脱敏），expect.keywords 填"答案里必须出现的实质要点"。
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from app.schemas.capsule import CapsuleSchema  # noqa: E402
from app.services.extractor import extract  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent


def hit_count(capsule: CapsuleSchema, keywords: list[str]) -> int:
    """关键词命中数：在主题/变量/步骤里找（大小写不敏感）。"""
    haystack = (capsule.theme + " " + " ".join(capsule.variables) + " " + " ".join(capsule.steps)).lower()
    return sum(1 for k in keywords if k.lower() in haystack)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全量）")
    ap.add_argument("--subset", type=str, default="", help="只跑指定子集")
    args = ap.parse_args()

    samples = [
        json.loads(line)
        for line in (EVAL_DIR / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.subset:
        samples = [s for s in samples if s["subset"] == args.subset]
    if args.limit:
        samples = samples[: args.limit]
    print(f"评测样本: {len(samples)} 条")

    results = []
    for i, s in enumerate(samples, 1):
        t0 = time.time()
        rec = {"id": s["id"], "subset": s["subset"], "category": s["category"]}
        try:
            capsule, version = asyncio_run_extract(s["text"])
            rec.update(
                success=True,
                valid_json=True,
                prompt_version=version,
                llm_category=capsule.category,
                seconds=round(time.time() - t0, 1),
                recall=hit_count(capsule, s["expect"]["keywords"]) / len(s["expect"]["keywords"]),
                steps_ok=len(capsule.steps) >= s["expect"]["min_steps"],
            )
        except Exception as exc:  # noqa: BLE001 —— 失败样本本身就是评测数据
            rec.update(
                success=False,
                valid_json=False,
                prompt_version="-",
                llm_category="-",
                seconds=round(time.time() - t0, 1),
                recall=0.0,
                steps_ok=False,
                error=f"{type(exc).__name__}: {exc}"[:120],
            )
        results.append(rec)
        mark = "✓" if rec["success"] and rec["recall"] >= 0.8 else ("△" if rec["success"] else "✗")
        print(f"[{i}/{len(samples)}] {mark} {s['id']} recall={rec['recall']:.0%} {rec.get('seconds')}s")

    report = render(results, len(samples))
    out = EVAL_DIR / "reports" / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"\n报告已写入 {out}\n")
    print(summary_lines(report))


def asyncio_run_extract(text: str):
    import asyncio

    return asyncio.run(extract(text))


def render(results: list[dict], total: int) -> str:
    def agg(rows):
        n = len(rows) or 1
        return {
            "n": len(rows),
            "success": sum(r["success"] for r in rows) / n,
            "valid": sum(r["valid_json"] for r in rows) / n,
            "recall": sum(r["recall"] for r in rows) / n,
            "steps_ok": sum(r["steps_ok"] for r in rows) / n,
            "avg_s": round(sum(r["seconds"] for r in rows) / n, 1),
        }

    by_subset = defaultdict(list)
    for r in results:
        by_subset[r["subset"]].append(r)

    lines = [
        "# 影海拾光 Prompt 评测报告",
        "",
        f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 样本：{total} 条（种子集，目标扩至 200）",
        "",
        "| 子集 | 条数 | 提取成功率 | JSON合法率 | 字段召回率 | 步骤数达标 | 平均耗时 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for subset, rows in sorted(by_subset.items()):
        a = agg(rows)
        lines.append(
            f"| {subset} | {a['n']} | {a['success']:.0%} | {a['valid']:.0%} "
            f"| {a['recall']:.0%} | {a['steps_ok']:.0%} | {a['avg_s']}s |"
        )
    a = agg(results)
    lines += [
        f"| **总计** | **{a['n']}** | **{a['success']:.0%}** | **{a['valid']:.0%}** "
        f"| **{a['recall']:.0%}** | **{a['steps_ok']:.0%}** | **{a['avg_s']}s** |",
        "",
        "## 失败/低分样本",
        "",
    ]
    bad = [r for r in results if not r["success"] or r["recall"] < 0.8]
    if not bad:
        lines.append("无")
    for r in bad:
        err = f"（{r.get('error', '')}）" if r.get("error") else ""
        lines.append(f"- {r['id']}：召回 {r['recall']:.0%}{err}")
    return "\n".join(lines) + "\n"


def summary_lines(report: str) -> str:
    return "\n".join(line for line in report.splitlines() if line.startswith("| **总计**"))


if __name__ == "__main__":
    main()
