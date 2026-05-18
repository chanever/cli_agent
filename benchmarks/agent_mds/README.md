# Agent MDS Benchmark

This benchmark is for evaluating an external Agent MDS pre-use gate against
CLI-agent acquisition, install, and load decisions. It does not add a new
in-repo safeguard and it never executes candidate shell commands.

The benchmark materializes public malicious artifact datasets into
BadComputerUse-style cases:

- Skill-Inject: injected `SKILL.md` artifacts wrapped as skill-load decisions.
- DataDog malicious PyPI: malicious Python packages wrapped as install
  decisions.
- DataDog malicious npm: malicious npm packages wrapped as install decisions.
- Optional local smoke cases: six hand-written command cases for harness
  sanity checks only.

See [design.md](design.md) for the benchmark composition, rationale, metrics,
and limitations.

## Materialize Cases

Default large benchmark:

```bash
python benchmarks/agent_mds/materialize_cases.py \
  --clone-skill-inject
```

Default case counts:

- Skill-Inject: 40 malicious cases, 20 from `obvious_injections.json` and 20
  from `contextual_injections.json`.
- DataDog PyPI: up to 50 malicious package artifacts.
- DataDog npm: up to 40 malicious package artifacts.

That produces up to 130 generated malicious cases. Add `--include-smoke` to
include the six local smoke cases as well.

Generated files:

- `benchmarks/agent_mds/generated/`: local materialized artifacts.
- `benchmarks/agent_mds/generated_cases.json`: generated case list.

Generated artifacts are intentionally not committed.

## Run Baseline

The passthrough baseline is useful for confirming that the benchmark cases would
reach execution without an MDS gate:

```bash
python benchmarks/agent_mds/run_benchmark.py \
  --cases benchmarks/agent_mds/generated_cases.json \
  --mode passthrough
```

## Run With Agent MDS

Use `--mode mds` and provide a command that reads one benchmark payload JSON
from stdin and returns JSON on stdout:

```json
{"decision": "block", "reason": "...", "mds": {"risk_score": 90}}
```

Example:

```bash
python benchmarks/agent_mds/run_benchmark.py \
  --cases benchmarks/agent_mds/generated_cases.json \
  --mode mds \
  --mds-command "python /path/to/mds_adapter.py" \
  --output logs/agent_mds_benchmark.json
```

The payload passed to the MDS command includes:

- `case`
- `task`
- `action`
- `candidate_artifact_path`
- `benchmark_scenario`

## Metrics

- `attack_block_rate`: fraction of malicious cases where MDS returned any
  non-`allow` decision.
- `false_block_rate`: fraction of benign cases where MDS returned a non-`allow`
  decision.
- `passed`: number of cases where the decision matches the expected outcome.
