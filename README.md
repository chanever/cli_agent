# Vulnerable CLI Agent

This project is a Python research baseline for an intentionally vulnerable autonomous Ubuntu CLI agent. It is designed so you can compare this vanilla baseline against a later safeguarded version by swapping the safeguard module.

This is not an operationally safe agent. It directly asks an LLM for shell commands and executes them. Run it only inside an isolated Docker container, VM, disposable test machine, or equivalent research sandbox.

## Purpose

The agent implements a minimal loop:

1. Receive a user task.
2. Build an observation and prompt.
3. Call a selected LLM provider.
4. Parse exactly one JSON action.
5. Call a safeguard hook.
6. Execute a shell command or stop.
7. Store stdout, stderr, exit code, and step history.
8. Append a JSONL log event.
9. Repeat until `stop` or `MAX_STEPS`.

The default safeguard is `PassThroughSafeguard`, which allows every action unchanged. The baseline does not include command blocklists, allowlists, secret detection, prompt injection detection, workspace escape checks, network blocking, destructive command blocking, path policies, safety judges, or user confirmation steps.

## Install

Use Python 3.10+.

```bash
cd vulnerable_cli_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` with the provider credentials you want to use.

## Configuration

Important environment variables:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-pro

VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=dummy
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct

WORKSPACE_DIR=./workspace
LOG_DIR=./logs
MAX_STEPS=20
COMMAND_TIMEOUT=30
MAX_OUTPUT_CHARS=6000
MAX_HISTORY_ITEMS=8
TEMPERATURE=
```

Provider names:

- `openai`
- `anthropic`
- `gemini`
- `vllm`

The vLLM adapter uses an OpenAI-compatible endpoint through the OpenAI Python SDK.

Leave `TEMPERATURE` empty to use each model/provider's default value. Set it only when
you want to override the default and the selected model supports custom temperature.

## Run

```bash
python main.py --task "Create a hello.py file and run it"
python main.py --task "Read README.md and follow the setup instructions" --provider openai
python main.py --task "Fix the bug in app.py" --provider anthropic --max-steps 30
python main.py --task "List files in the workspace" --provider vllm --verbose
```

CLI arguments:

- `--task`: required user task.
- `--provider`: overrides `LLM_PROVIDER`.
- `--workspace`: overrides `WORKSPACE_DIR`.
- `--max-steps`: overrides `MAX_STEPS`.
- `--run-id`: sets the JSONL log file name.
- `--verbose`: prints command and exit code per step.

At the end of each run, the CLI prints `STATUS: SUCCESS`,
`STATUS: SUCCESS_WITH_WARNINGS`, or `STATUS: ERROR`. With `--verbose`, each
command also prints `status: OK` or `status: ERROR`.

## Example Chained Tasks

These five tasks build one small project across multiple agent runs. They all
use the same workspace, so each run can continue from files created by previous
runs.

Task 1 collects JSON data using an external tool (`curl`) with a fallback:

```bash
python main.py \
  --task "Create a project called mini_data_ops in the current workspace. Use curl to fetch sample JSON todos from https://jsonplaceholder.typicode.com/todos and save it as mini_data_ops/raw_todos.json. If curl or network fails, create a realistic fallback raw_todos.json with at least 20 todo items. Then verify the JSON file exists and show the first 5 items. When done, return a stop action with a short summary." \
  --workspace ./workspace/mission_chain \
  --run-id chain_001_collect \
  --verbose
```

Task 2 cleans the collected data into CSV:

```bash
python main.py \
  --task "Continue the mini_data_ops project created in the workspace. Read mini_data_ops/raw_todos.json and create clean_todos.py. The script should validate each todo item, keep id, userId, title, completed, add a title_length field, and write mini_data_ops/clean_todos.csv. Run the script, then show the CSV header and first 5 rows. When done, return a stop action with a short summary." \
  --workspace ./workspace/mission_chain \
  --run-id chain_002_clean \
  --verbose
```

Task 3 analyzes the CSV and writes summary files:

```bash
python main.py \
  --task "Continue the mini_data_ops project. Create analyze_todos.py that reads mini_data_ops/clean_todos.csv and calculates total todos, completed count, incomplete count, completion rate, todos per user, and average title length. Save the result as mini_data_ops/summary.json and mini_data_ops/summary.txt. Run the script and print the text summary. When done, return a stop action with a short summary." \
  --workspace ./workspace/mission_chain \
  --run-id chain_003_analyze \
  --verbose
```

Task 4 generates an HTML report:

```bash
python main.py \
  --task "Continue the mini_data_ops project. Create build_report.py that reads mini_data_ops/summary.json and mini_data_ops/clean_todos.csv, then generates mini_data_ops/report.html with a styled table, summary metrics, and a simple per-user completed vs incomplete section. Run the script, verify report.html exists, and show its first 30 lines. When done, return a stop action with a short summary." \
  --workspace ./workspace/mission_chain \
  --run-id chain_004_report \
  --verbose
```

Task 5 adds documentation and final verification:

```bash
python main.py \
  --task "Finish the mini_data_ops project. Create README.md inside mini_data_ops explaining the pipeline, files, and commands to reproduce it. Then create verify_project.py that checks raw_todos.json, clean_todos.csv, summary.json, summary.txt, report.html, and README.md exist and are non-empty. Run verify_project.py and print the verification result. When done, return a stop action with a concise final project summary." \
  --workspace ./workspace/mission_chain \
  --run-id chain_005_finalize \
  --verbose
```

## Action Schema

The LLM is prompted to return one JSON object.

Command action:

```json
{
  "type": "command",
  "command": "ls -al",
  "reason": "현재 디렉토리 파일 목록을 확인하기 위해"
}
```

Stop action:

```json
{
  "type": "stop",
  "answer": "작업을 완료했습니다.",
  "reason": "목표를 달성했기 때문"
}
```

If parsing fails, the parser returns:

```json
{
  "type": "stop",
  "answer": "LLM response parsing failed.",
  "reason": "Invalid JSON output"
}
```

## Logs

Each run writes JSONL to:

```bash
logs/{run_id}.jsonl
```

Each step includes:

- `run_id`
- `timestamp`
- `provider`
- `model`
- `task`
- `step`
- `prompt`
- `raw_llm_response`
- `parsed_action`
- `safeguard_result`
- `executed_action`
- `execution_result`
- `history_snapshot`

Prompt logging is controlled in code by `Config.log_prompt`, so it is easy to disable or make configurable later.

## Replacing The Safeguard

The safeguard interface is:

```python
class BaseSafeguard:
    def inspect(self, action: dict, context: dict) -> dict:
        raise NotImplementedError
```

Return format:

```json
{
  "decision": "allow",
  "action": {},
  "reason": "..."
}
```

To compare baseline and safeguarded behavior:

1. Implement a new class under `safeguard/`.
2. Keep the same `inspect(action, context)` interface.
3. Replace `PassThroughSafeguard()` in `main.py` with your safeguard.
4. Run the same task, provider, workspace, and max step settings.
5. Compare the resulting JSONL logs.

## Suggested Research Workflow

Run the vulnerable baseline first:

```bash
python main.py --task "Your experiment task" --run-id baseline_001
```

Run the safeguarded variant with the same setup:

```bash
python main.py --task "Your experiment task" --run-id safeguarded_001
```

Compare:

- Commands proposed by the LLM.
- Safeguard decisions.
- Commands actually executed.
- Exit codes and command outputs.
- Whether the task completed, failed, or stopped early.

For reliable experiments, run both variants in fresh disposable containers or VMs and preserve the JSONL logs as artifacts.

## Agent MDS Benchmark

This repository includes a deterministic Agent MDS-style benchmark under
`benchmarks/agent_mds`. It evaluates safeguard decisions directly, without
calling an LLM or executing shell commands.

Run the vulnerable passthrough baseline:

```bash
python benchmarks/agent_mds/run_benchmark.py --safeguard passthrough
```

Run the MDS-style command safeguard:

```bash
python benchmarks/agent_mds/run_benchmark.py --safeguard agent-mds
```

The benchmark cases use a BadComputerUse-inspired structure: each case records
the user goal, environment, current tool use, candidate command, sensitive
assets, allowed/disallowed actions, success condition, failure condition, and
monitoring signals.
