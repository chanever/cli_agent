"""Command line entrypoint for the vulnerable CLI agent."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agent.runner import AgentRunner
from config import Config
from llm.factory import create_llm_client
from safeguard.passthrough import PassThroughSafeguard


def create_safeguard():
    """Create the selected safeguard.

    Shadow mode is the project default; passthrough remains available for the
    original vulnerable baseline experiments.
    """
    mode = os.getenv("SAFEGUARD_MODE", "shadow").lower()
    framework_disabled = os.getenv("SECURITY_FRAMEWORK_ENABLED", "true").lower() in {"0", "false", "no", "off"}
    if mode in {"passthrough", "baseline"} or framework_disabled:
        return PassThroughSafeguard()
    if mode in {"shadow", "shadow_sandbox"}:
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from security_framework.safeguard.shadow_sandbox_safeguard import ShadowSandboxSafeguard

        return ShadowSandboxSafeguard()
    raise ValueError(f"Unsupported SAFEGUARD_MODE: {mode}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Research baseline vulnerable CLI agent.")
    parser.add_argument("--task", required=True, help="Task for the agent to complete.")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini", "vllm"], help="LLM provider.")
    parser.add_argument("--workspace", help="Workspace directory used as command cwd.")
    parser.add_argument("--max-steps", type=int, help="Maximum agent loop steps.")
    parser.add_argument("--run-id", help="Optional run identifier used for JSONL logs.")
    parser.add_argument("--verbose", action="store_true", help="Print step details while running.")
    return parser.parse_args()


def main() -> None:
    """Configure and run the agent."""
    args = parse_args()
    config = Config().resolve_paths()
    if args.provider:
        config.llm_provider = args.provider
    if args.workspace:
        config.workspace_dir = args.workspace
    if args.max_steps is not None:
        config.max_steps = args.max_steps
    config.resolve_paths()

    llm_client = create_llm_client(config.llm_provider, config)
    safeguard = create_safeguard()
    runner = AgentRunner(config=config, llm_client=llm_client, safeguard=safeguard, verbose=args.verbose)
    result = runner.run(task=args.task, run_id=args.run_id)

    status = result.get("status", "error")
    if status == "success":
        print("STATUS: SUCCESS")
    elif status == "success_with_warnings":
        print("STATUS: SUCCESS_WITH_WARNINGS")
        print(f"WARNING: {result.get('error')}")
    elif status == "blocked":
        print("STATUS: BLOCKED")
        print(f"BLOCKED: {result.get('error') or result.get('answer', '')}")
    else:
        print("STATUS: ERROR")
        print(f"ERROR: {result.get('error') or result.get('answer', '')}")

    answer = result.get("answer", "")
    if answer and answer != result.get("error"):
        print(answer)
    print(f"run_id={result.get('run_id')}")
    print(f"log_file={result.get('log_file')}")
    if status in {"error", "blocked"}:
        sys.exit(1)


if __name__ == "__main__":
    main()
