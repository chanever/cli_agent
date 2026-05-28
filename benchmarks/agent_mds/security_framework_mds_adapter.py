"""Adapter that exposes this repo's security framework as an Agent MDS command.

The benchmark runner sends one JSON payload on stdin and expects one JSON object
on stdout. This adapter performs pre-use analysis only: it builds an Evidence
Package, runs optional static/reputation analysis, calls the Claude verifier,
and returns an allow/block decision. It does not execute the candidate command.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
VULNERABLE_AGENT_ROOT = THIS_FILE.parents[2]
PROJECT_ROOT = THIS_FILE.parents[3]
SECURITY_FRAMEWORK_ROOT = PROJECT_ROOT / "security_framework"

for path in (VULNERABLE_AGENT_ROOT, SECURITY_FRAMEWORK_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from dotenv import load_dotenv

    load_dotenv(VULNERABLE_AGENT_ROOT / ".env")
except Exception:
    pass

from security_framework.analysis.reputation_analyzer import analyze_reputation  # noqa: E402
from security_framework.analysis.static_analyzer import analyze_static  # noqa: E402
from security_framework.classification.asset_kind_classifier import classify_asset_kind  # noqa: E402
from security_framework.classification.external_target_extractor import extract_external_targets  # noqa: E402
from security_framework.classification.trigger import classify_command  # noqa: E402
from security_framework.config import SecurityFrameworkConfig  # noqa: E402
from security_framework.evidence.evidence_builder import build_evidence_package  # noqa: E402
from security_framework.verifier import verify  # noqa: E402


def _candidate_path(payload: dict) -> Path | None:
    raw = payload.get("candidate_artifact_path")
    if not raw:
        return None
    path = Path(str(raw)).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path


def _context(payload: dict, candidate_path: Path | None) -> dict:
    cwd = candidate_path if candidate_path and candidate_path.is_dir() else PROJECT_ROOT
    return {
        "task": payload.get("task", ""),
        "step": 0,
        "run_id": payload.get("case", {}).get("case_id", "agent_mds_case").replace("/", "_").replace(":", "_"),
        "cwd": str(cwd),
        "history": [],
        "last_result": None,
        "benchmark_scenario": payload.get("benchmark_scenario") or {},
        "candidate_artifact_path": str(candidate_path) if candidate_path else None,
        "external_origin": bool(candidate_path),
    }


def _targets(action: dict, context: dict, classification: dict, candidate_path: Path | None) -> list[dict]:
    targets = list(classification.get("targets") or extract_external_targets(action, context, classification))
    if candidate_path and candidate_path.exists() and not any(t.get("type") == "local_package" for t in targets):
        targets.append({"type": "local_package", "path": ".", "source": str(candidate_path)})
    return targets


def _external_analysis(action: dict, context: dict, classification: dict, targets: list[dict], cfg: SecurityFrameworkConfig) -> dict:
    asset_kind = classify_asset_kind(action, context, classification, targets, cfg)
    static_result = {"status": "skipped", "findings": [], "summary": "No analysis was requested."}
    reputation_result = {"status": "skipped", "signals": [], "summary": "No analysis was requested."}

    if asset_kind.get("status") == "completed":
        if cfg.static_analysis_enabled:
            static_result = analyze_static(action, context, targets, classification, asset_kind)
        if cfg.reputation_analysis_enabled:
            reputation_result = analyze_reputation(action, context, targets, classification, asset_kind)
    else:
        static_result = {"status": "skipped", "findings": [], "summary": "Asset kind was not confidently classified."}
        reputation_result = {"status": "skipped", "signals": [], "summary": "Asset kind was not confidently classified."}

    return {
        "targets": targets,
        "asset_kind": asset_kind,
        "static_analysis": static_result,
        "reputation_analysis": reputation_result,
    }


def evaluate(payload: dict) -> dict:
    action = payload.get("action") or {}
    candidate_path = _candidate_path(payload)
    context = _context(payload, candidate_path)
    cfg = SecurityFrameworkConfig.from_env().resolve_paths()

    classification = classify_command(action.get("command", ""), context)
    targets = _targets(action, context, classification, candidate_path)
    classification["targets"] = targets
    if targets:
        classification["external_env"] = True
    external_analysis = _external_analysis(action, context, classification, targets, cfg)
    evidence_package = build_evidence_package(
        payload.get("task", ""),
        context,
        action,
        classification,
        sandbox_result=None,
        semantic_trace=None,
        external_interaction_analysis=external_analysis,
    )
    verifier_result = verify(evidence_package, cfg)

    verifier_decision = str(verifier_result.get("decision", "HOLD")).upper()
    decision = "allow" if verifier_decision == "ALLOW" else "block"
    return {
        "decision": decision,
        "reason": verifier_result.get("reason", ""),
        "mds": {
            "verifier_decision": verifier_decision,
            "reason_source": verifier_result.get("reason_source", ""),
            "risk_level": verifier_result.get("risk_level"),
            "risk_score": verifier_result.get("risk_score"),
            "asset_kind": external_analysis.get("asset_kind"),
            "static_analysis": {
                "status": external_analysis.get("static_analysis", {}).get("status"),
                "summary": external_analysis.get("static_analysis", {}).get("summary"),
                "findings_count": len(external_analysis.get("static_analysis", {}).get("findings") or []),
            },
            "reputation_analysis": {
                "status": external_analysis.get("reputation_analysis", {}).get("status"),
                "summary": external_analysis.get("reputation_analysis", {}).get("summary"),
                "signals_count": len(external_analysis.get("reputation_analysis", {}).get("signals") or []),
            },
            "classification": classification,
        },
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        result = evaluate(payload)
    except Exception as exc:
        result = {
            "decision": "error",
            "reason": f"security framework MDS adapter failed: {exc}",
            "mds": {"exception_type": type(exc).__name__},
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
