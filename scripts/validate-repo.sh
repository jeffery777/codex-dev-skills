#!/usr/bin/env bash
# Public repository hygiene checks for codex-dev-skills.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_PYTHON="$ROOT_DIR/scripts/project-python"
cd "$ROOT_DIR"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

ok() {
  if [[ "${UNIT_TEST_GROUP_SKIPPED:-false}" == true ]]; then
    printf '[SKIP] embedded unit-test group: %s\n' "$*"
    UNIT_TEST_GROUP_SKIPPED=false
    return
  fi
  printf '[OK] %s\n' "$*"
}

SKIP_UNIT_TESTS=false
UNIT_TEST_GROUP_SKIPPED=false

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --skip-unit-tests)
        "$SKIP_UNIT_TESTS" && fail "duplicate option: $1"
        SKIP_UNIT_TESTS=true
        ;;
      --)
        fail "unexpected option: $1"
        ;;
      -*)
        fail "unknown option: $1"
        ;;
      *)
        fail "unexpected positional argument: $1"
        ;;
    esac
    shift
  done
}

run_unit_tests() {
  if [[ "$SKIP_UNIT_TESTS" == true ]]; then
    UNIT_TEST_GROUP_SKIPPED=true
    return
  fi
  "$PROJECT_PYTHON" -m unittest "$@" >/dev/null
}

parse_args "$@"

TMP_BASE="${TMPDIR:-/tmp}"
case "$TMP_BASE" in
  /*) ;;
  *) fail "TMPDIR must be absolute: $TMP_BASE" ;;
esac
TMP_BASE_REAL="$(cd "$TMP_BASE" && pwd -P)"
case "$TMP_BASE_REAL" in
  "$ROOT_DIR"|"$ROOT_DIR"/*) fail "TMPDIR must not resolve inside the repository: $TMP_BASE_REAL" ;;
esac
TMP_DIR="$(mktemp -d "$TMP_BASE_REAL/codex-dev-skills-validate.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

require_rg() {
  command -v rg >/dev/null 2>&1 || fail "ripgrep (rg) is required"
}

check_no_provider_terms() {
  local pattern
  pattern="$(printf '%s|%s|%s|%s|%s' cl'aude' anthrop'ic' sonn'et' op'us' hai'ku')"
  if rg -i "$pattern" . >"$TMP_DIR/provider-hits.txt"; then
    cat "$TMP_DIR/provider-hits.txt"
    fail "excluded provider terms found"
  fi
  ok "excluded provider terms absent"
}

check_sensitive_private_terms() {
  local private_pattern
  private_pattern="$(printf '%s|%s' '/''Users/' yang'chunchih')"
  if rg -i "$private_pattern" . >"$TMP_DIR/private-hits.txt"; then
    cat "$TMP_DIR/private-hits.txt"
    fail "private path or user identifier found"
  fi
  ok "private paths and local user identifiers absent"

  local review_pattern review_count
  review_pattern="$(printf '%s|%s|%s|%s|%s|%s' tok'en' sec'ret' au'th' SQL'ite' sess'ion' ca'che')"
  if rg -i "$review_pattern" . >"$TMP_DIR/sensitive-review.txt"; then
    review_count="$(wc -l <"$TMP_DIR/sensitive-review.txt" | tr -d ' ')"
    printf '[INFO] sensitive-term review produced %s policy/source hit(s); showing first 20:\n' "$review_count"
    sed -n '1,20p' "$TMP_DIR/sensitive-review.txt"
    if [[ "$review_count" -gt 20 ]]; then
      printf '[INFO] sensitive-term review output truncated; run a targeted rg search when full inspection is needed.\n'
    fi
  else
    ok "sensitive-term review produced no hits"
  fi
}

check_legacy_private_names() {
  local pattern
  pattern="$(printf '%s|%s|%s|%s' 'u''1_' 'shared''_' 'codex''_merge_' 'dual''-engine')"
  if rg -n "$pattern" . \
    --glob '!scripts/validate-repo.sh' >"$TMP_DIR/legacy-hits.txt"; then
    cat "$TMP_DIR/legacy-hits.txt"
    fail "legacy private names found"
  fi
  ok "legacy private names absent"
}

check_catalog_sources() {
  local path missing=0
  while IFS= read -r path; do
    case "$path" in
      /*|~*|*\$*|*'..'*)
        printf '[FAIL] unsafe catalog source path: %s\n' "$path" >&2
        missing=1
        continue
        ;;
    esac
    [[ -e "$path" ]] || {
      printf '[FAIL] catalog source missing: %s\n' "$path" >&2
      missing=1
    }
    [[ ! -L "$path" ]] || {
      printf '[FAIL] catalog source must not be a symlink: %s\n' "$path" >&2
      missing=1
    }
    if [[ -d "$path" ]] && find "$path" -type l -print -quit | grep -q .; then
      printf '[FAIL] catalog source directory contains symlink(s): %s\n' "$path" >&2
      find "$path" -type l -print >&2
      missing=1
    fi
  done < <(sed -n 's/^[[:space:]]*- source:[[:space:]]*//p' catalog.yaml)
  [[ "$missing" -eq 0 ]] || exit 1
  ok "catalog sources exist"
}

check_catalog_skill_metadata() {
  "$PROJECT_PYTHON" - <<'PY'
from pathlib import Path

import yaml

catalog = yaml.safe_load(Path("catalog.yaml").read_text(encoding="utf-8"))
groups = catalog.get("groups", {})
skill_entries = [
    entry
    for group in groups.values()
    for entry in group.get("skills", [])
]
skill_sources = {entry["source"] for entry in skill_entries}
allowed_statuses = {
    "active-desktop-adapter",
    "deprecated-compatibility-alias",
}

for entry in skill_entries:
    source = entry["source"]
    status = entry.get("status")
    routes = entry.get("routes_to")
    if status is not None and status not in allowed_statuses:
        raise SystemExit(f"invalid catalog skill status for {source}: {status}")
    if routes is not None:
        if not isinstance(routes, list) or not routes:
            raise SystemExit(f"catalog routes_to must be a non-empty list for {source}")
        missing = sorted(set(routes) - skill_sources)
        if missing:
            raise SystemExit(
                f"catalog routes_to for {source} references missing skills: {missing}"
            )
    if status == "deprecated-compatibility-alias" and routes is None:
        raise SystemExit(f"deprecated catalog alias lacks routes_to: {source}")
    if status != "deprecated-compatibility-alias" and routes is not None:
        raise SystemExit(f"only deprecated catalog aliases may declare routes_to: {source}")
PY
  ok "catalog skill lifecycle and routes metadata are valid"
}

check_installer_catalog_consistency() {
  local catalog_list installer_list
  catalog_list="$TMP_DIR/catalog-sources.txt"
  installer_list="$TMP_DIR/installer-sources.txt"
  sed -n 's/^[[:space:]]*- source:[[:space:]]*//p' catalog.yaml | sort -u > "$catalog_list"
  ./install.sh manifest | sed -n 's/^.* source: //p' | sort -u > "$installer_list"
  if ! diff -u "$catalog_list" "$installer_list"; then
    fail "catalog.yaml and install.sh manifest differ"
  fi
  ok "catalog and installer manifest match"
}

check_code_mode_tool_policy() {
  "$PROJECT_PYTHON" scripts/validate-code-mode-tool-policy.py
  run_unit_tests tests.test_code_mode_tool_policy
  ok "Code Mode tool policy references and isolated packaging contracts pass"
}

check_installer_target_modes() {
  local legacy_manifest agents_manifest
  legacy_manifest="$TMP_DIR/installer-legacy-manifest.txt"
  agents_manifest="$TMP_DIR/installer-agents-manifest.txt"

  ./install.sh help > "$TMP_DIR/install-help.txt"
  rg -F -q 'by default' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the default skills target"
  rg -F -q 'CODEX_DEV_SKILLS_TARGET=legacy' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document CODEX_DEV_SKILLS_TARGET=legacy"
  rg -F -q '~/.codex/skills/<skill>/' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the legacy skills target"
  rg -F -q '~/.agents/skills/<skill>/' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the agents skills target"
  rg -F -q '~/.codex/agents/<profile>.toml' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the opt-in custom-agent target"
  rg -F -q 'excluded from --all' "$TMP_DIR/install-help.txt" \
    || fail "installer help must state that custom-agent profiles are excluded from --all"

  CODEX_DEV_SKILLS_TARGET=legacy ./install.sh manifest | sort -u > "$legacy_manifest"
  ./install.sh manifest | sort -u > "$agents_manifest"
  if ! diff -u "$legacy_manifest" "$agents_manifest"; then
    fail "installer manifests must not differ by target mode"
  fi
  if CODEX_DEV_SKILLS_TARGET=invalid ./install.sh help >"$TMP_DIR/install-invalid.out" 2>"$TMP_DIR/install-invalid.err"; then
    fail "invalid CODEX_DEV_SKILLS_TARGET must fail closed"
  fi
  ok "installer target modes are documented and fail closed"
}

check_release_state() {
  "$PROJECT_PYTHON" scripts/validate-release-state.py
  run_unit_tests tests.test_release_state_contract
  ok "offline release-state structural and source/package checks are valid"
}

frontmatter_value() {
  local key="$1" file="$2"
  sed -n "2,/^---\$/s/^$key:[[:space:]]*//p" "$file" | head -n 1
}

check_skill_metadata() {
  local skill expected name description missing=0
  while IFS= read -r skill; do
    expected="$(basename "$(dirname "$skill")")"
    name="$(frontmatter_value name "$skill")"
    description="$(frontmatter_value description "$skill")"
    if [[ -z "$name" ]]; then
      printf '[FAIL] missing skill front matter name: %s\n' "$skill" >&2
      missing=1
    elif [[ "$name" != "$expected" ]]; then
      printf '[FAIL] skill name mismatch: %s declares %s, expected %s\n' "$skill" "$name" "$expected" >&2
      missing=1
    fi
    if [[ -z "$description" ]]; then
      printf '[FAIL] missing skill front matter description: %s\n' "$skill" >&2
      missing=1
    fi
    if ! rg -q '^Runtime compatibility:[[:space:]]*(shared|cli|desktop|plugin-dependent)$' "$skill"; then
      printf '[FAIL] missing runtime compatibility: %s\n' "$skill" >&2
      missing=1
    fi
  done < <(find skills -name SKILL.md -print | sort)
  [[ "$missing" -eq 0 ]] || exit 1
  ok "all skills declare required metadata"
}

check_loop_ledger() {
  "$PROJECT_PYTHON" scripts/validate-loop-ledger.py
}

check_loop_eval() {
  "$PROJECT_PYTHON" scripts/eval-loop-engineering.py >"$TMP_DIR/loop-eval.json"
  ok "loop engineering workflow eval thresholds pass"
}

check_context_continuity() {
  "$PROJECT_PYTHON" scripts/eval-context-continuity.py >"$TMP_DIR/context-continuity-eval.json"
  run_unit_tests tests.test_context_continuity tests.test_eval_context_continuity
  ok "context continuity decisions, rollover guards, and cost/quality evals pass"
}

check_agent_profiles() {
  "$PROJECT_PYTHON" scripts/validate-agent-profiles.py >"$TMP_DIR/agent-profiles.json"
  run_unit_tests tests.test_agent_profiles tests.test_installer_agent_profiles
  ok "custom-agent profiles and isolated installer contracts pass"
}

check_agent_routing_eval() {
  "$PROJECT_PYTHON" scripts/eval-agent-routing.py >"$TMP_DIR/agent-routing-eval.json"
  run_unit_tests tests.test_agent_routing tests.test_eval_agent_routing
  ok "heterogeneous agent routing eval thresholds pass"
}

check_memory_contract() {
  "$PROJECT_PYTHON" scripts/eval-memory-contract.py >"$TMP_DIR/memory-contract-eval.json"
  run_unit_tests tests.test_memory_contract tests.test_memoryctl tests.test_eval_memory_contract
  ok "external memory contract, CLI, and eval thresholds pass"
}

check_operational_evidence_contract() {
  "$PROJECT_PYTHON" scripts/eval-operational-evidence.py >"$TMP_DIR/operational-evidence-eval.json"
  run_unit_tests \
    tests.test_operational_evidence \
    tests.test_evidencectl \
    tests.test_eval_operational_evidence
  ok "operational evidence contract, CLI, fixtures, and eval thresholds pass"
}

check_improvement_lineage_contract() {
  "$PROJECT_PYTHON" scripts/eval-improvement-lineage.py >"$TMP_DIR/improvement-lineage-eval.json"
  run_unit_tests \
    tests.test_improvement_lineage \
    tests.test_improvementctl \
    tests.test_eval_improvement_lineage \
    tests.test_improvement_lineage_contract_docs
  ok "improvement lineage and deterministic projection contracts pass"
}

check_improvement_proposal_contract() {
  "$PROJECT_PYTHON" scripts/eval-improvement-proposal.py >"$TMP_DIR/improvement-proposal-eval.json"
  run_unit_tests \
    tests.test_improvement_proposal \
    tests.test_proposalctl \
    tests.test_eval_improvement_proposal \
    tests.test_improvement_proposal_contract_docs
  ok "proposal-only evidence-to-proposal contracts pass"
}

check_candidate_evaluation_contract() {
  "$PROJECT_PYTHON" scripts/eval-candidate-evaluation.py >"$TMP_DIR/candidate-evaluation-eval.json"
  run_unit_tests \
    tests.test_candidate_evaluation \
    tests.test_evaluationctl \
    tests.test_eval_candidate_evaluation \
    tests.test_candidate_evaluation_contract_docs
  ok "isolated candidate evaluation, replay, context, packet, and eval contracts pass"
}

check_memory_m0_contracts() {
  "$PROJECT_PYTHON" scripts/eval-memory-operation.py >"$TMP_DIR/memory-operation-eval.json"
  "$PROJECT_PYTHON" scripts/eval-memory-qualification.py >"$TMP_DIR/memory-qualification-eval.json"
  run_unit_tests \
    tests.test_memory_operation \
    tests.test_operationctl \
    tests.test_eval_memory_operation \
    tests.test_memory_qualification \
    tests.test_qualificationctl \
    tests.test_eval_memory_qualification \
    tests.test_memory_m0_contract_docs
  ok "Memory M0 operation authority, atomic receipt, zero-touch, and qualification contracts pass"
}

check_memory_m1_contracts() {
  "$PROJECT_PYTHON" scripts/eval-memory-sqlite.py >"$TMP_DIR/memory-sqlite-eval.json"
  run_unit_tests \
    tests.test_memory_sqlite \
    tests.test_sqlitectl \
    tests.test_eval_memory_sqlite \
    tests.test_memory_sqlite_contract_docs
  ok "Memory M1 SQLite/FTS5 reference adapter safety and conformance contracts pass"
}

check_loop_contract() {
  run_unit_tests tests.test_loop_engineering_core tests.test_loopctl
  ok "loop engineering event, transition, migration, and CLI contracts pass"
}

check_native_runtime_contract() {
  run_unit_tests \
    tests.test_cli_session_handoff \
    tests.test_native_runtime_contract_docs \
    tests.test_project_python
  ok "native CLI/Desktop runtime adapter contracts pass"
}

check_desktop_wrapper_security_fixtures() {
  run_unit_tests tests.test_desktop_wrapper_security_fixtures
  ok "wrapper-independent Desktop security invariants pass"
}

check_plugin_package() {
  "$PROJECT_PYTHON" scripts/sync-plugin-package.py >/dev/null
  ok "plugin package exact inventory and canonical parity are valid"
}

check_repository_guardrails() {
  "$PROJECT_PYTHON" scripts/validate-gitnexus-config.py >"$TMP_DIR/gitnexus-config.json"
  run_unit_tests \
    tests.test_gitnexus_config_guard \
    tests.test_pr_issue_link
  ok "GitNexus and pull request linkage repository guardrails pass"
}

check_test_shards() {
  "$PROJECT_PYTHON" scripts/test-shards.py validate >"$TMP_DIR/test-shards.txt"
  run_unit_tests tests.test_test_shards
  ok "repository test shard manifest is a complete exact partition"
}

main() {
  require_rg
  check_no_provider_terms
  check_sensitive_private_terms
  check_legacy_private_names
  check_repository_guardrails
  check_test_shards
  check_catalog_sources
  check_catalog_skill_metadata
  check_installer_catalog_consistency
  check_code_mode_tool_policy
  check_plugin_package
  check_installer_target_modes
  check_release_state
  check_skill_metadata
  check_loop_ledger
  check_loop_contract
  check_desktop_wrapper_security_fixtures
  check_native_runtime_contract
  check_loop_eval
  check_context_continuity
  check_agent_profiles
  check_agent_routing_eval
  check_memory_contract
  check_operational_evidence_contract
  check_improvement_lineage_contract
  check_improvement_proposal_contract
  check_candidate_evaluation_contract
  check_memory_m0_contracts
  check_memory_m1_contracts
}

main "$@"
