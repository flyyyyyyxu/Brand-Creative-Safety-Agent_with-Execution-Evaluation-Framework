#!/usr/bin/env python3
import argparse
import json
import os
import time
import random

DATA_PATH = "datasets/tasks.json"
ARTIFACTS_DIR = "artifacts"
RUNS_PATH = os.path.join(ARTIFACTS_DIR, "runs.jsonl")


def load_tasks():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def simulate_llm_answer(query, strategy):
    """
    模拟不同策略的差异（先不用真实模型）
    """

    base_answer = f"Analysis regarding: {query}"

    if strategy == "A":
        # 自由生成，风险更高
        label = random.choice(["safe", "unsafe"])
        hallucination_risk = random.uniform(0.4, 0.9)

    elif strategy == "B":
        # allowlist only
        label = "safe"
        hallucination_risk = random.uniform(0.1, 0.4)

    else:  # C
        label = "safe"
        hallucination_risk = random.uniform(0.0, 0.2)

    return {
        "final_answer": base_answer,
        "label": label,
        "scores": {
            "brand_safety": random.uniform(0.6, 0.95),
            "policy_risk": random.uniform(0.0, 0.5),
            "hallucination_risk": hallucination_risk,
            "evidence_quality": random.uniform(0.5, 0.9),
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_id", required=True)
    parser.add_argument("--strategy_id", required=True)
    args = parser.parse_args()

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    data = load_tasks()

    task = None
    for t in data["tasks"]:
        if t["task_id"] == args.task_id:
            task = t
            break

    if not task:
        raise ValueError("Task not found")

    result = simulate_llm_answer(task["query"], args.strategy_id)

    run_record = {
        "task_id": task["task_id"],
        "strategy_id": args.strategy_id,
        "brand": data["brand"],
        "query": task["query"],
        "topic": task["topic"],
        "started_at": time.time(),
        "final_answer": result["final_answer"],
        "label": result["label"],
        "scores": result["scores"]
    }

    with open(RUNS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(run_record) + "\n")

    print("Run completed and written to artifacts/runs.jsonl")


if __name__ == "__main__":
    main()