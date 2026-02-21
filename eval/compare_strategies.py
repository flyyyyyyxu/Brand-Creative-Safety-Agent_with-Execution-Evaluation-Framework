
#!/usr/bin/env python3
# Compares strategies based on artifacts/summary.json produced by eval/analyze.py
# Standard library only.

import argparse
import json
import os

DEFAULT_SUMMARY = os.path.join("artifacts", "summary.json")
DEFAULT_REPORT = os.path.join("artifacts", "report.md")


def _num(x):
    return f"{x:0.3f}" if isinstance(x, (int, float)) else "n/a"


def _pct(x):
    return f"{x*100:0.1f}%" if isinstance(x, (int, float)) else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=DEFAULT_SUMMARY, help="Path to artifacts/summary.json")
    ap.add_argument("--out", default=DEFAULT_REPORT, help="Path to write artifacts/report.md")
    args = ap.parse_args()

    if not os.path.exists(args.summary):
        raise FileNotFoundError(f"summary not found: {args.summary} (run eval/analyze.py first)")

    with open(args.summary, "r", encoding="utf-8") as f:
        s = json.load(f)

    overall = s.get("overall", {})
    strategies = s.get("strategies", {})
    tasks = s.get("tasks", {})

    # rank strategies: prefer higher safe_rate, lower unsafe_rate
    def key_fn(item):
        name, v = item
        return (v.get("safe_rate", 0.0), -v.get("unsafe_rate", 0.0), v.get("runs", 0))

    ranked = sorted(strategies.items(), key=key_fn, reverse=True)

    lines = []
    lines.append("# Brand Creative Safety Agent — Strategy Comparison Report\n")
    lines.append(f"- Total runs: **{overall.get('runs', 0)}**\n")
    lines.append(f"- Safe rate: **{_pct(overall.get('safe_rate'))}** | Unsafe rate: **{_pct(overall.get('unsafe_rate'))}** | Unknown rate: **{_pct(overall.get('unknown_rate'))}**\n")
    lines.append("\n## Strategy leaderboard\n")
    lines.append("| Rank | Strategy | Runs | Safe | Unsafe | Unknown | Avg brand_safety | Avg policy_risk | Avg hallucination_risk | Avg evidence_quality |\n")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")

    for i, (name, v) in enumerate(ranked, start=1):
        avg = v.get("avg_scores", {})
        lines.append(
            f"| {i} | `{name}` | {v.get('runs',0)} | {_pct(v.get('safe_rate'))} | {_pct(v.get('unsafe_rate'))} | {_pct(v.get('unknown_rate'))} "
            f"| {_num(avg.get('brand_safety'))} | {_num(avg.get('policy_risk'))} | {_num(avg.get('hallucination_risk'))} | {_num(avg.get('evidence_quality'))} |\n"
        )

    lines.append("\n## Task breakdown\n")
    lines.append("| Task | Runs | Safe | Unsafe | Unknown |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for task_id, v in sorted(tasks.items(), key=lambda kv: kv[0]):
        lines.append(
            f"| `{task_id}` | {v.get('runs',0)} | {_pct(v.get('safe_rate'))} | {_pct(v.get('unsafe_rate'))} | {_pct(v.get('unknown_rate'))} |\n"
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Wrote report: {args.out}")


if __name__ == "__main__":
    main()
