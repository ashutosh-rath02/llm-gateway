import argparse
import json
from dataclasses import asdict
from pathlib import Path

import httpx

from app.evals.runner import compare_eval_summaries, summarize_eval_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Gateway eval utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export eval dataset from the gateway")
    export_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    export_parser.add_argument("--out", required=True)
    export_parser.add_argument("--feature")
    export_parser.add_argument("--task-type")
    export_parser.add_argument("--model")
    export_parser.add_argument("--status")
    export_parser.add_argument("--tenant-id")
    export_parser.add_argument("--fallback-used", choices=["true", "false"])
    export_parser.add_argument("--prompt-template-name")
    export_parser.add_argument("--prompt-template-version")
    export_parser.add_argument("--limit", type=int, default=100)

    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Summarize an exported JSONL dataset",
    )
    summarize_parser.add_argument("--dataset", required=True)

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two exported JSONL datasets",
    )
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)

    args = parser.parse_args()

    if args.command == "export":
        _run_export(args)
        return
    if args.command == "summarize":
        _run_summarize(args.dataset)
        return
    _run_compare(args.baseline, args.candidate)


def _run_export(args) -> None:
    payload = {
        "feature": args.feature,
        "task_type": args.task_type,
        "model": args.model,
        "status": args.status,
        "tenant_id": args.tenant_id,
        "fallback_used": (
            None
            if args.fallback_used is None
            else args.fallback_used == "true"
        ),
        "prompt_template_name": args.prompt_template_name,
        "prompt_template_version": args.prompt_template_version,
        "limit": args.limit,
    }
    payload = {key: value for key, value in payload.items() if value is not None}

    response = httpx.post(
        f"{args.base_url.rstrip('/')}/v1/evals/export",
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    output_path = Path(args.out)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in data.get("items", []):
            handle.write(json.dumps(item))
            handle.write("\n")

    print(
        json.dumps(
            {
                "written": len(data.get("items", [])),
                "path": str(output_path),
                "filters": data.get("filters", {}),
            }
        )
    )


def _run_summarize(dataset_path: str) -> None:
    items = _load_jsonl(dataset_path)
    print(json.dumps(asdict(summarize_eval_dataset(items)), indent=2))


def _run_compare(baseline_path: str, candidate_path: str) -> None:
    baseline_summary = summarize_eval_dataset(_load_jsonl(baseline_path))
    candidate_summary = summarize_eval_dataset(_load_jsonl(candidate_path))
    print(json.dumps(compare_eval_summaries(baseline_summary, candidate_summary), indent=2))


def _load_jsonl(path: str) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    main()
