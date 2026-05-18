"""Agent loop orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.memory import AgentMemory
from agent.parser import parse_action
from agent.prompt import build_messages, build_prompt
from config import Config
from logging_utils.jsonl_logger import JsonlLogger
from safeguard.base import BaseSafeguard
from shell.executor import run_command


class AgentRunner:
    """Runs the vulnerable command-generating agent loop."""

    def __init__(self, config: Config, llm_client: Any, safeguard: BaseSafeguard, verbose: bool = False) -> None:
        self.config = config
        self.llm_client = llm_client
        self.safeguard = safeguard
        self.verbose = verbose

    def run(self, task: str, run_id: str | None = None) -> dict:
        """Run the agent until stop or max_steps."""
        run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        workspace = Path(self.config.workspace_dir)
        log_dir = Path(self.config.log_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = JsonlLogger(log_dir / f"{run_id}.jsonl")
        memory = AgentMemory(max_items=self.config.max_history_items)
        last_result: dict | None = None
        answer = "Max steps reached."
        status = "error"
        error = "Max steps reached."
        had_command_error = False

        for step in range(self.config.max_steps):
            prompt = build_prompt(task=task, cwd=str(workspace), history=memory.recent(), last_result=last_result)
            raw_response = self.llm_client.generate(
                build_messages(prompt),
                temperature=self.config.temperature,
            )
            parsed_action = parse_action(raw_response)
            context = {
                "task": task,
                "step": step,
                "cwd": str(workspace),
                "history": memory.recent(),
                "last_result": last_result,
            }
            safeguard_result = self.safeguard.inspect(parsed_action, context)
            executed_action = safeguard_result.get("action", parsed_action)
            execution_result = None

            if safeguard_result.get("decision") == "block":
                answer = safeguard_result.get("reason", "Action blocked.")
                status = "error"
                error = answer
                execution_result = {"success": False, "stdout": "", "stderr": answer, "exit_code": None, "timed_out": False}
                memory.add(step, executed_action, execution_result)
                self._log_step(logger, run_id, task, step, prompt, raw_response, parsed_action, safeguard_result, executed_action, execution_result, memory)
                break

            if executed_action.get("type") == "command":
                execution_result = run_command(
                    command=executed_action.get("command", ""),
                    cwd=str(workspace),
                    timeout=self.config.command_timeout,
                    max_output_chars=self.config.max_output_chars,
                )
                last_result = execution_result
                if not execution_result.get("success"):
                    had_command_error = True
                memory.add(step, executed_action, execution_result)
                if self.verbose:
                    self._print_verbose_command_result(step, executed_action, execution_result)
            elif executed_action.get("type") == "stop":
                answer = executed_action.get("answer", "")
                execution_result = {"success": True, "stdout": answer, "stderr": "", "exit_code": 0, "timed_out": False}
                if answer == "LLM response parsing failed.":
                    status = "error"
                    error = answer
                elif had_command_error:
                    status = "success_with_warnings"
                    error = "One or more commands failed before the agent completed."
                else:
                    status = "success"
                    error = ""
                memory.add(step, executed_action, execution_result)
                self._log_step(logger, run_id, task, step, prompt, raw_response, parsed_action, safeguard_result, executed_action, execution_result, memory)
                break
            else:
                answer = "Unknown action type."
                status = "error"
                error = answer
                execution_result = {"success": False, "stdout": "", "stderr": answer, "exit_code": None, "timed_out": False}
                memory.add(step, executed_action, execution_result)
                self._log_step(logger, run_id, task, step, prompt, raw_response, parsed_action, safeguard_result, executed_action, execution_result, memory)
                break

            self._log_step(logger, run_id, task, step, prompt, raw_response, parsed_action, safeguard_result, executed_action, execution_result, memory)

        return {"run_id": run_id, "answer": answer, "log_file": str(logger.path), "status": status, "error": error}

    def _print_verbose_command_result(self, step: int, action: dict, result: dict) -> None:
        """Print command progress in a terminal-friendly format."""
        print(f"[step {step}] command: {action.get('command')}")
        print(f"[step {step}] exit_code: {result.get('exit_code')}")
        if result.get("success"):
            print(f"[step {step}] status: OK")
            return

        print(f"[step {step}] status: ERROR")
        stderr = (result.get("stderr") or "").strip()
        stdout = (result.get("stdout") or "").strip()
        if stderr:
            print(f"[step {step}] stderr: {stderr}")
        elif stdout:
            print(f"[step {step}] stdout: {stdout}")

    def _log_step(
        self,
        logger: JsonlLogger,
        run_id: str,
        task: str,
        step: int,
        prompt: str,
        raw_response: str,
        parsed_action: dict,
        safeguard_result: dict,
        executed_action: dict,
        execution_result: dict | None,
        memory: AgentMemory,
    ) -> None:
        """Write one JSONL log event."""
        logger.write(
            {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": self.config.llm_provider,
                "model": self.config.model_for_provider(),
                "task": task,
                "step": step,
                "prompt": prompt if self.config.log_prompt else None,
                "raw_llm_response": raw_response,
                "parsed_action": parsed_action,
                "safeguard_result": safeguard_result,
                "executed_action": executed_action,
                "execution_result": execution_result,
                "history_snapshot": memory.snapshot(),
            }
        )
