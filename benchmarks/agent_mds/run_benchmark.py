"""Run Agent MDS-style safeguard benchmark cases.

The runner evaluates safeguard decisions directly, without calling an LLM or
executing shell commands. This keeps the benchmark deterministic and suitable
for comparing the vulnerable passthrough baseline with a safeguarded variant.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from safeguard.agent_mds import AgentMDSSafeguard  # noqa: E402
from safeguard.passthrough import PassThroughSafeguard  # noqa: E402

DEFAULT_CASES = Path(__file__).with_name("cases.json")


def load_safeguard(spec: str):
    """Load a safeguard from shorthand or module:Class."""
    if spec == "passthrough":
        return PassThroughSafeguard()
    if spec == "agent-mds":
        return AgentMDSSafeguard()
    if ":" not in spec:
        raise ValueError("custom safeguard must use module:Class")
    module_name, class_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("case file must contain a JSON list")
    return data


def evaluate_case(case: dict[str, Any], safeguard) -> dict[str, Any]:
    action = case["action"]
    context = {
        "task": case["task"],
        "step": 0,
        "cwd": "<benchmark-workspace>",
        "history": [],
        "last_result": None,
        "benchmark_scenario": case.get("benchmark_scenario") or {},
    }
    decision = safeguard.inspect(action, context)
    actual = str(decision.get("decision") or "")
    expected = str(case["expected_decision"])
    return {
        "case_id": case["case_id"],
        "task": case["task"],
        "expected_decision": expected,
        "actual_decision": actual,
        "passed": actual == expected,
        "reason": decision.get("reason"),
        "mds": decision.get("mds"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    block_cases = [row for row in rows if row["expected_decision"] == "block"]
    allow_cases = [row for row in rows if row["expected_decision"] == "allow"]
    blocked = sum(1 for row in block_cases if row["actual_decision"] == "block")
    false_blocks = sum(1 for row in allow_cases if row["actual_decision"] == "block")
    return {
        "cases": len(rows),
        "passed": sum(1 for row in rows if row["passed"]),
        "failed": sum(1 for row in rows if not row["passed"]),
        "block_cases": len(block_cases),
        "allow_cases": len(allow_cases),
        "attack_block_rate": blocked / len(block_cases) if block_cases else None,
        "false_block_rate": false_blocks / len(allow_cases) if allow_cases else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent MDS safeguard benchmark")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--safeguard",
        default="agent-mds",
        help="passthrough, agent-mds, or module:Class",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    safeguard = load_safeguard(args.safeguard)
    rows = [evaluate_case(case, safeguard) for case in load_cases(args.cases)]
    report = {
        "safeguard": args.safeguard,
        "summary": summarize(rows),
        "rows": rows,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
