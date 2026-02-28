import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
BOT_LOG = BASE_DIR.parent / "5_evil_docs" / "query_logs.jsonl"


def load_jsonl(path: Path):
    items = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def latest_golden_log() -> Path | None:
    candidates = sorted(LOGS_DIR.glob("golden_run_*.jsonl"))
    if not candidates:
        return None
    return candidates[-1]


def analyze_golden(log_items: list[dict]):
    failures = [x for x in log_items if not x.get("is_correct", False)]
    missing_by_topic = Counter()
    bad_sources = Counter()

    for item in failures:
        missing_by_topic[item.get("topic", "unknown")] += 1
        expected = set(item.get("expected_sources", []))
        found = set(item.get("found_sources", []))
        if expected and found and expected.isdisjoint(found):
            for src in found:
                bad_sources[src] += 1

    return {
        "total": len(log_items),
        "failures": len(failures),
        "failure_by_topic": dict(missing_by_topic),
        "top_irrelevant_sources": bad_sources.most_common(10),
    }


def analyze_bot_logs(log_items: list[dict]):
    total = len(log_items)
    no_chunks = sum(1 for x in log_items if not x.get("chunks_found", False))
    unsuccessful = sum(1 for x in log_items if not x.get("successful_answer", False))

    source_counter = Counter()
    for item in log_items:
        for src in item.get("sources", []):
            source_counter[src] += 1

    return {
        "total_queries": total,
        "no_chunks_queries": no_chunks,
        "unsuccessful_answers": unsuccessful,
        "top_sources": source_counter.most_common(10),
    }


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = defaultdict(dict)

    golden_log = latest_golden_log()
    if golden_log:
        summary["golden"] = analyze_golden(load_jsonl(golden_log))
        summary["golden"]["log_path"] = str(golden_log)
    else:
        summary["golden"] = {"error": "golden log not found"}

    summary["bot_queries"] = analyze_bot_logs(load_jsonl(BOT_LOG))
    summary["bot_queries"]["log_path"] = str(BOT_LOG)

    report_path = REPORTS_DIR / "analytics_summary.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSummary saved to: {report_path}")


if __name__ == "__main__":
    main()
