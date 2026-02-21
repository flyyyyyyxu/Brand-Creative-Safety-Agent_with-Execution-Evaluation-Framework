
#!/usr/bin/env python3
# Minimal evaluator: reads artifacts/runs.jsonl and produces artifacts/summary.json
# Standard library only.

import argparse
import json
import os
from collections import defaultdict, Counter
from statistics import mean

DEFAULT_RUNS = os.path.join("artifacts", "runs.jsonl")
DEFAULT_OUT = os.path.join("artifacts", "summary.json")

LABEL_KEYS = ["label", "verdict", "safety_label", "result"]
STRATEGY_KEYS = ["strategy_id", "strategy", "strategy_name"]
TASK_KEYS = ["task_id", "task", "id"]

SCORE_CANDIDATES = ["brand_safety", "policy_risk", "hallucination_risk", "evidence_quality"]


def _first_present(d, keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _normalize_label(run: dict) -> str:
    # try direct
    lbl = _first_present(run, LABEL_KEYS)
    if isinstance(lbl, str):
        lbl = lbl.strip().lower()
        if lbl in ("safe", "unsafe", "unknown"):
            return lbl

    # try nested labels dict
    labels = run.get("labels")
    if isinstance(labels, dict):
        for k in LABEL_KEYS:
            v = labels.get(k)
            if isinstance(v, str):
                v = v.strip().lower()
                if v in ("safe", "unsafe", "unknown"):
                    return v
        # common pattern: labels={"brand_safety":"safe"}
        for v in labels.values():
            if isinstance(v, str):
                vv = v.strip().lower()
                if vv in ("safe", "unsafe", "unknown"):
                    return vv

    return "unknown"


def _extract_scores(run: dict) -> dict:
    scores = {}
    raw = run.get("scores")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, (int, float)):
                scores[k] = float(v)

    # allow top-level scores too
    for k in SCORE_CANDIDATES:
        v = run.get(k)
        if isinstance(v, (int, float)):
            scores[k] = float(v)

    # keep only in [0,1] when possible (but don't hard fail)
    clean = {}
    for k, v in scores.items():
        if isinstance(v, float) and (0.0 <= v <= 1.0):
            clean[k] = v
        elif isinstance(v, float):
            # clamp gently to avoid breaking aggregation
            clean[k] = max(0.0, min(1.0, v))
    return clean


def _read_jsonl(path: str):
    runs = []
    if not os.path.exists(path):
        raise FileNotFoundError(f"Runs file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    runs.append(obj)
            except json.JSONDecodeError:
                # keep going, but mark the line
                runs.append({"error": f"invalid_json_line_{i}", "raw": line})
    return runs


def _safe_mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return mean(vals) if vals else None


def analyze(runs: list[dict]) -> dict:
    # group by strategy, task
    per_strategy = defaultdict(list)
    per_task = defaultdict(list)

    normalized = []
    for r in runs:
        task_id = _first_present(r, TASK_KEYS, default=r.get("task_id", "unknown"))
        strat = _first_present(r, STRATEGY_KEYS, default="unknown")
        final_answer = r.get("final_answer") or r.get("answer") or r.get("final") or ""

        nr = {
            "task_id": str(task_id),
            "strategy_id": str(strat),
            "topic": r.get("topic") or r.get("category") or "",
            "query": r.get("query") or r.get("prompt") or "",
            "final_answer": final_answer,
            "label": _normalize_label(r),
            "scores": _extract_scores(r),
            "has_error": bool(r.get("error")) or str(r.get("status","")).lower() in ("error","failed"),
        }
        normalized.append(nr)
        per_strategy[nr["strategy_id"]].append(nr)
        per_task[nr["task_id"]].append(nr)

    # overall
    label_counts = Counter([r["label"] for r in normalized])
    overall = {
        "runs": len(normalized),
        "labels": dict(label_counts),
        "unsafe_rate": (label_counts["unsafe"] / len(normalized)) if normalized else 0.0,
        "safe_rate": (label_counts["safe"] / len(normalized)) if normalized else 0.0,
        "unknown_rate": (label_counts["unknown"] / len(normalized)) if normalized else 0.0,
        "error_runs": sum(1 for r in normalized if r["has_error"]),
    }

    # strategy summaries
    strategies = {}
    for strat, items in per_strategy.items():
        c = Counter([x["label"] for x in items])
        scores_by_key = defaultdict(list)
        for x in items:
            for k, v in x["scores"].items():
                scores_by_key[k].append(v)

        strategies[strat] = {
            "runs": len(items),
            "labels": dict(c),
            "unsafe_rate": (c["unsafe"] / len(items)) if items else 0.0,
            "safe_rate": (c["safe"] / len(items)) if items else 0.0,
            "unknown_rate": (c["unknown"] / len(items)) if items else 0.0,
            "avg_scores": {k: _safe_mean(vs) for k, vs in scores_by_key.items()},
        }

    # task summaries
    tasks = {}
    for task_id, items in per_task.items():
        c = Counter([x["label"] for x in items])
        tasks[task_id] = {
            "runs": len(items),
            "labels": dict(c),
            "unsafe_rate": (c["unsafe"] / len(items)) if items else 0.0,
            "safe_rate": (c["safe"] / len(items)) if items else 0.0,
            "unknown_rate": (c["unknown"] / len(items)) if items else 0.0,
        }

    return {"overall": overall, "strategies": strategies, "tasks": tasks}


def _print_table(summary: dict):
    # simple fixed-width table
    strategies = summary.get("strategies", {})
    rows = []
    for s, v in sorted(strategies.items(), key=lambda kv: kv[0]):
        rows.append((
            s,
            v.get("runs", 0),
            v.get("safe_rate", 0.0),
            v.get("unsafe_rate", 0.0),
            v.get("unknown_rate", 0.0),
            v.get("avg_scores", {}).get("brand_safety"),
            v.get("avg_scores", {}).get("policy_risk"),
            v.get("avg_scores", {}).get("hallucination_risk"),
            v.get("avg_scores", {}).get("evidence_quality"),
        ))

    headers = ["strategy", "runs", "safe%", "unsafe%", "unk%", "brand_safety", "policy_risk", "halluc_risk", "evidence_q"]
    fmt = "{:<14} {:>5} {:>7} {:>7} {:>7} {:>12} {:>11} {:>11} {:>11}"
    print(fmt.format(*headers))
    print("-" * 92)
    for r in rows:
        def pct(x): return f"{x*100:5.1f}" if isinstance(x, (int,float)) else "  n/a"
        def num(x): return f"{x:0.3f}" if isinstance(x, (int,float)) else "n/a"
        print(fmt.format(
            r[0], r[1], pct(r[2]), pct(r[3]), pct(r[4]),
            num(r[5]), num(r[6]), num(r[7]), num(r[8])
        ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=DEFAULT_RUNS, help="Path to artifacts/runs.jsonl")
    ap.add_argument("--out", default=DEFAULT_OUT, help="Path to write artifacts/summary.json")
    ap.add_argument("--print", action="store_true", help="Print summary table to stdout")
    args = ap.parse_args()

    runs = _read_jsonl(args.runs)
    summary = analyze(runs)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if args.print:
        print(f"\nLoaded runs: {summary['overall']['runs']} | unsafe_rate={summary['overall']['unsafe_rate']:.3f} | safe_rate={summary['overall']['safe_rate']:.3f}")
        _print_table(summary)
        print(f"\nWrote: {args.out}\n")


if __name__ == "__main__":
    main()
