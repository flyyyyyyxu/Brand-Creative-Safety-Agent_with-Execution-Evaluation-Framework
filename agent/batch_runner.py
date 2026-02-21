#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

def main():
    # 读取 tasks.json
    with open("datasets/tasks.json") as f:
        config = json.load(f)
    
    tasks = config["tasks"]
    strategies = config["strategies"]
    repeat = config.get("repeat_per_strategy", 3)
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_ids", help="Comma-separated task IDs (e.g., T1,T2,T3)")
    parser.add_argument("--all_tasks", action="store_true")
    parser.add_argument("--all_strategies", action="store_true")
    parser.add_argument("--repeat", type=int, default=repeat)
    args = parser.parse_args()
    
    # 选择任务
    if args.all_tasks:
        selected_tasks = tasks
    elif args.task_ids:
        task_ids = args.task_ids.split(",")
        selected_tasks = [t for t in tasks if t["task_id"] in task_ids]
    else:
        print("Error: specify --all_tasks or --task_ids")
        sys.exit(1)
    
    # 选择策略
    if args.all_strategies:
        selected_strategies = list(strategies.keys())
    else:
        selected_strategies = ["A"]  # 默认只跑 A
    
    total_runs = len(selected_tasks) * len(selected_strategies) * args.repeat
    print(f"Running {total_runs} total runs")
    
    run_count = 0
    for task in selected_tasks:
        for strategy_id in selected_strategies:
            for i in range(args.repeat):
                run_count += 1
                print(f"\n[{run_count}/{total_runs}] {task['task_id']} | Strategy {strategy_id} | Run {i+1}/{args.repeat}")
                
                cmd = [
                    "python3", "agent/agent.py",
                    "--task_id", task["task_id"],
                    "--strategy_id", strategy_id,
                    "--timeout", "90",
                    "--max_steps", "8"
                ]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print("... success")
                    else:
                        print(f"... failed: {result.stderr[:100]}")
                except subprocess.TimeoutExpired:
                    print("... timeout")

if __name__ == "__main__":
    main()