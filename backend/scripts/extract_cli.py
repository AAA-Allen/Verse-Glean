"""端到端验证 CLI（DEVELOPMENT_PLAN T1.8）：

    python scripts/extract_cli.py "【B站】10分钟学会VLOOKUP https://b23.tv/xxxx"
    python scripts/extract_cli.py --manual "粘贴的视频文案..."

依赖：后端已启动（默认 http://127.0.0.1:8000），.env 已配置 DashScope Key。
"""
import argparse
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = "dev-single-user-token"  # 与 backend/.env 的 YHSG_API_TOKEN 一致


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="分享口令/链接 或（--manual）文案")
    ap.add_argument("--manual", action="store_true")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--timeout", type=float, default=180)
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {TOKEN}"}
    body = {"manual_text": args.text} if args.manual else {"share_text": args.text}

    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{args.base}/extractions", json=body, headers=headers)
        resp.raise_for_status()
        task = resp.json()["data"]
        task_id = task["task_id"]
        print(f"[submit] task_id={task_id} status={task['status']}")

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            time.sleep(2)
            data = client.get(f"{args.base}/extractions/{task_id}", headers=headers).json()["data"]
            print(f"[poll] status={data['status']}")
            if data["status"] in ("done", "failed"):
                break

        if data["status"] != "done":
            print(f"[fail] {data.get('stage_error')}")
            return 1

        capsule_id = data["capsule_id"]
        capsule = client.get(f"{args.base}/capsules/{capsule_id}", headers=headers).json()["data"]
        print("\n=== 知识胶囊 ===")
        print(f"主题: {capsule['theme']}")
        print(f"垂类: {capsule['category']}  prompt: {capsule['prompt_version']}")
        print(f"变量: {capsule['variables']}")
        print("步骤:")
        for i, s in enumerate(capsule["steps"], 1):
            print(f"  {i}. {s}")
        print(f"标签: {capsule['tags']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
