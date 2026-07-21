#!/usr/bin/env bash
# Codex-only installer for codex-dev-skills.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills"
STATE_FILE="$STATE_DIR/installed.jsonl"
PROFILE_STATE_FILE=""
DEFAULT_CODEX_LEGACY_SKILLS_DIR="$HOME/.codex/skills"
DEFAULT_CODEX_AGENTS_SKILLS_DIR="$HOME/.agents/skills"
DEFAULT_CODEX_TEMPLATES_DIR="$HOME/.codex/templates"
DEFAULT_CODEX_CUSTOM_AGENTS_DIR="$HOME/.codex/agents"
CODEX_DEV_SKILLS_TARGET="${CODEX_DEV_SKILLS_TARGET:-legacy}"
CODEX_TEMPLATES_DIR="${CODEX_TEMPLATES_DIR:-$DEFAULT_CODEX_TEMPLATES_DIR}"
CODEX_CUSTOM_AGENTS_DIR="${CODEX_CUSTOM_AGENTS_DIR:-$DEFAULT_CODEX_CUSTOM_AGENTS_DIR}"
VERSION="0.8.1"

case "$CODEX_DEV_SKILLS_TARGET" in
  legacy) DEFAULT_CODEX_SKILLS_DIR="$DEFAULT_CODEX_LEGACY_SKILLS_DIR" ;;
  agents) DEFAULT_CODEX_SKILLS_DIR="$DEFAULT_CODEX_AGENTS_SKILLS_DIR" ;;
  *)
    printf '[ERROR] CODEX_DEV_SKILLS_TARGET must be '\''legacy'\'' or '\''agents'\'': %s\n' "$CODEX_DEV_SKILLS_TARGET" >&2
    exit 1
    ;;
esac

CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$DEFAULT_CODEX_SKILLS_DIR}"

usage() {
  cat <<'USAGE'
Usage:
  ./install.sh list
  ./install.sh install <group>
  ./install.sh install --all
  ./install.sh update <group>
  ./install.sh update --all
  ./install.sh update <group> --force
  ./install.sh status
  ./install.sh diff <group>
  ./install.sh diff --all
  ./install.sh uninstall <group> --yes
  ./install.sh uninstall --all --yes

Groups:
  shared-review-gates
  codex-review-workflow
  codex-delivery-workflow
  desktop-delivery-workflow
  codex-agent-profiles (explicit opt-in; excluded from --all)

Targets:
  Codex skills:    ~/.codex/skills/<skill>/ by default
                   ~/.agents/skills/<skill>/ when CODEX_DEV_SKILLS_TARGET=agents
  Codex templates: ~/.codex/templates/...
  Custom agents:   ~/.codex/agents/<profile>.toml by default
                   Set CODEX_CUSTOM_AGENTS_DIR=<trusted-project>/.codex/agents with
                   CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES for project adoption.

This installer never overwrites ~/.codex/AGENTS.md.
Custom CODEX_SKILLS_DIR / CODEX_TEMPLATES_DIR / CODEX_CUSTOM_AGENTS_DIR values require CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES.
The default target remains legacy to avoid changing existing installations.
The codex-agent-profiles group is never installed by --all or codex-dev-skills.
USAGE
}

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

absolute_path() {
  local path="$1"
  case "$path" in
    /*) printf '%s\n' "$path" ;;
    *) printf '%s\n' "$PWD/$path" ;;
  esac
}

reject_suspicious_relpath() {
  local rel="$1"
  [[ -n "$rel" ]] || die "Empty target path"
  case "$rel" in
    /*|~*|*\$*|*'..'*) die "Unsafe target path: $rel" ;;
  esac
}

reject_symlink_components() {
  local path component current
  local -a parts=()
  path="$(absolute_path "$1")"
  path="${path%/}"
  current=""
  IFS='/' read -r -a parts <<< "$path"
  for component in "${parts[@]}"; do
    [[ -z "$component" ]] && continue
    current="$current/$component"
    [[ -L "$current" ]] && die "Refusing symlink target component: $current"
  done
  return 0
}

canonicalize_root() {
  local raw="$1" default_raw="$2" label="$3" abs default_abs real_abs
  abs="$(absolute_path "$raw")"
  default_abs="$(absolute_path "$default_raw")"
  if [[ "$abs" != "$default_abs" ]]; then
    if [[ "${CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS:-}" != "YES" ]]; then
      die "$label override requires CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES: $raw"
    fi
    reject_suspicious_root_path "$raw" "$label"
    reject_custom_root "$abs" "$label"
  fi
  reject_symlink_components "$abs"
  mkdir -p "$abs"
  real_abs="$(cd "$abs" && pwd -P)"
  if [[ "$abs" != "$default_abs" ]]; then
    reject_custom_root "$real_abs" "$label"
  fi
  printf '%s\n' "$real_abs"
}

reject_custom_root() {
  local abs="$1" label="$2" expected_base home_abs home_parent home_codex home_agents
  home_abs="$(absolute_path "$HOME")"
  home_parent="$(dirname "$home_abs")"
  home_codex="$home_abs/.codex"
  home_agents="$home_abs/.agents"
  case "$label" in
    CODEX_SKILLS_DIR) expected_base="skills" ;;
    CODEX_TEMPLATES_DIR) expected_base="templates" ;;
    CODEX_CUSTOM_AGENTS_DIR) expected_base="agents" ;;
    *) expected_base="" ;;
  esac
  case "$abs" in
    /|"$home_abs"|"$home_parent"|"$home_codex"|"$home_agents")
      die "$label custom root is too broad: $abs"
      ;;
  esac
  if [[ -n "$expected_base" && "$(basename "$abs")" != "$expected_base" ]]; then
    die "$label custom root must end with '$expected_base': $abs"
  fi
}

reject_suspicious_root_path() {
  local raw="$1" label="$2"
  [[ -n "$raw" ]] || die "$label custom root is empty"
  case "$raw" in
    ~*|*\$*|*'..'*) die "$label custom root contains unsafe path syntax: $raw" ;;
  esac
}

init_targets() {
  CODEX_SKILLS_DIR="$(canonicalize_root "$CODEX_SKILLS_DIR" "$DEFAULT_CODEX_SKILLS_DIR" "CODEX_SKILLS_DIR")" || return 1
  CODEX_TEMPLATES_DIR="$(canonicalize_root "$CODEX_TEMPLATES_DIR" "$DEFAULT_CODEX_TEMPLATES_DIR" "CODEX_TEMPLATES_DIR")" || return 1
}

init_agent_target() {
  CODEX_CUSTOM_AGENTS_DIR="$(canonicalize_root "$CODEX_CUSTOM_AGENTS_DIR" "$DEFAULT_CODEX_CUSTOM_AGENTS_DIR" "CODEX_CUSTOM_AGENTS_DIR")" || return 1
  PROFILE_STATE_FILE="$STATE_DIR/agent-profile-$(python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' "$CODEX_CUSTOM_AGENTS_DIR").tsv"
}

safe_path_under_root() {
  local root="$1" rel="$2" path
  reject_suspicious_relpath "$rel"
  path="$root/$rel"
  reject_symlink_components "$path"
  printf '%s\n' "$path"
}

safe_backup_path() {
  local dst="$1" backup="$dst.bak"
  reject_symlink_components "$backup"
  [[ ! -e "$backup" ]] || die "Refusing to overwrite existing backup path: $backup"
  printf '%s\n' "$backup"
}

all_groups() {
  printf '%s\n' \
    shared-review-gates \
    codex-review-workflow \
    codex-delivery-workflow \
    desktop-delivery-workflow \
    codex-agent-profiles
}

default_groups() {
  printf '%s\n' \
    shared-review-gates \
    codex-review-workflow \
    codex-delivery-workflow \
    desktop-delivery-workflow
}

group_exists() {
  case "$1" in
    shared-review-gates|codex-review-workflow|codex-delivery-workflow|desktop-delivery-workflow|codex-agent-profiles) return 0 ;;
    codex-dev-skills) return 0 ;;
    *) return 1 ;;
  esac
}

group_description() {
  case "$1" in
    shared-review-gates) echo "Shared review gates, closure triage, safety policies, and orchestration templates." ;;
    codex-review-workflow) echo "Routine and deep code, docs, and merge review workflows." ;;
    codex-delivery-workflow) echo "Loop engineering, planning, bounded implementation, docs update, and delegated delivery workflows." ;;
    desktop-delivery-workflow) echo "Thin Codex Desktop task, thread, worktree, scheduling, and integration adapters." ;;
    codex-agent-profiles) echo "Opt-in Loop Engineering V2a custom-agent runtime profiles." ;;
    codex-dev-skills) echo "Alias for all groups." ;;
  esac
}

group_deps() {
  case "$1" in
    shared-review-gates) : ;;
    codex-review-workflow) echo "shared-review-gates" ;;
    codex-delivery-workflow) echo "shared-review-gates" ;;
    desktop-delivery-workflow) echo "shared-review-gates codex-delivery-workflow" ;;
    codex-agent-profiles) echo "shared-review-gates codex-delivery-workflow" ;;
    codex-dev-skills) default_groups ;;
  esac
}

group_skills() {
  case "$1" in
    shared-review-gates)
      printf '%s\n' closure-triage task-continuation code-review-gate docs-review-gate merge-readiness-gate review-artifact-cleanup ;;
    codex-review-workflow)
      printf '%s\n' code-review code-review-deep docs-review merge-review merge-review-deep ;;
    codex-delivery-workflow)
      printf '%s\n' loop-engineering planning milestone-continuation project-delivery project-orchestrator implementation-slice docs-update ;;
    desktop-delivery-workflow)
      printf '%s\n' desktop-project-delivery desktop-thread-delegation desktop-spec-plan-gate desktop-implementation-gate desktop-pr-merge-gate ;;
    codex-agent-profiles) : ;;
  esac
}

group_agent_profiles() {
  case "$1" in
    codex-agent-profiles)
      printf '%s\n' \
        agent-profiles/loop_v2a_mechanical_reader.toml \
        agent-profiles/loop_v2a_fast_explorer.toml \
        agent-profiles/loop_v2a_balanced_worker.toml \
        agent-profiles/loop_v2a_advanced_worker.toml \
        agent-profiles/loop_v2a_deep_reviewer.toml \
        agent-profiles/loop_v2a_exceptional_researcher.toml \
        agent-profiles/loop_v2a_security_reviewer.toml ;;
  esac
}

group_templates() {
  case "$1" in
    shared-review-gates)
      printf '%s\n' \
        policies/agent-delegation-policy.md \
        policies/delivery-drift-control-policy.md \
        policies/human-gate-policy.md \
        policies/model-selection-policy.md \
        policies/multi-agent-integration-policy.md \
        policies/project-agent-knowledge-policy.md \
        policies/projectspec-alignment-policy.md \
        policies/reusable-workflow-contract.md \
        policies/review-artifact-policy.md \
        policies/runtime-compatibility-policy.md \
        policies/security-review-escalation-policy.md \
        templates/orchestration/agent-task-brief.template.md \
        templates/orchestration/agent-routing-integration.template.yaml \
        templates/orchestration/closure-triage-overlay.template.yaml \
        templates/orchestration/current-task-summary.template.md \
        templates/orchestration/implementation-plan.template.md \
        templates/orchestration/integration-review-report.template.md \
        templates/orchestration/next-session-prompt.template.md \
        templates/orchestration/orchestrator-gate-report.template.md \
        templates/orchestration/project-spec.template.md \
        templates/orchestration/task-continuation-report.template.md \
        templates/orchestration/task-manifest.template.yaml ;;
    codex-review-workflow)
      printf '%s\n' \
        templates/review/code-review-report.template.md \
        templates/review/merge-review-report.template.md \
        templates/review/review-follow-up.template.md \
        workflows/review-workflow.md \
        workflows/merge-readiness-workflow.md ;;
    codex-delivery-workflow)
      printf '%s\n' \
        docs/native-runtime-capabilities.md \
        templates/orchestration/loop-engineering-spec.template.md \
        templates/orchestration/loop-decision-input.template.yaml \
        templates/orchestration/loop-event.template.yaml \
        templates/orchestration/loop-handoff-prompt.template.md \
        templates/orchestration/loop-iteration-report.template.md \
        templates/orchestration/loop-state-ledger.template.yaml \
        templates/orchestration/task-claim-lease.template.yaml \
        workflows/implementation-workflow.md \
        workflows/loop-engineering-workflow.md ;;
    desktop-delivery-workflow)
      printf '%s\n' workflows/desktop-delivery-workflow.md ;;
  esac
}

template_target() {
  local rel="$1"
  case "$rel" in
    policies/*) printf '%s\n' "orchestration/$rel" ;;
    templates/*) printf '%s\n' "${rel#templates/}" ;;
    workflows/*) printf '%s\n' "$rel" ;;
    *) printf '%s\n' "$rel" ;;
  esac
}

ensure_group() {
  group_exists "$1" || die "Unknown group: $1. Run ./install.sh list."
}

expand_groups() {
  local requested="$1" seen="" result="" group dep
  if [[ "$requested" == "--all" || "$requested" == "codex-dev-skills" ]]; then
    requested="$(default_groups | tr '\n' ' ')"
  fi
  for group in $requested; do
    ensure_group "$group"
    for dep in $(group_deps "$group"); do
      case " $seen " in *" $dep "*) ;; *) seen="$seen $dep"; result="$result $dep" ;; esac
    done
    case " $seen " in *" $group "*) ;; *) seen="$seen $group"; result="$result $group" ;; esac
  done
  printf '%s\n' $result
}

record_state() {
  local action="$1" group="$2" ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$STATE_DIR"
  printf '{"repo":"codex-dev-skills","version":"%s","action":"%s","group":"%s","installed_at":"%s"}\n' \
    "$VERSION" "$action" "$group" "$ts" >> "$STATE_FILE"
}

remove_transient_skill_files() {
  local root="$1"
  find "$root" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
  find "$root" -depth -type d -name '__pycache__' -empty -delete
}

install_skill() {
  local skill="$1" src dst
  src="$ROOT_DIR/skills/$skill"
  dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
  [[ -d "$src" ]] || die "Missing skill source: skills/$skill"
  mkdir -p "$dst"
  cp -R "$src"/. "$dst"/
  remove_transient_skill_files "$dst"
  ok "skill $skill"
}

install_template() {
  local rel="$1" target_rel src dst
  target_rel="$(template_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
  [[ -f "$src" ]] || die "Missing template source: $rel"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  ok "template $target_rel"
}

profile_target() {
  basename "$1"
}

install_agent_profile() {
  local rel="$1" src dst target_rel
  target_rel="$(profile_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
  [[ -f "$src" && ! -L "$src" ]] || die "Missing or unsafe agent profile source: $rel"
  sync_file "$src" "$dst" "agent profile $target_rel" 0
}

file_sha256() {
  python3 -c 'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$1"
}

validate_agent_profile_sources() {
  local validator registry
  validator="$ROOT_DIR/skills/loop-engineering/scripts/profile_preflight.py"
  registry="$ROOT_DIR/skills/loop-engineering/references/agent-profile-registry.json"
  [[ -f "$validator" && ! -L "$validator" ]] || die "Missing or unsafe agent profile validator: $validator"
  [[ -f "$registry" && ! -L "$registry" ]] || die "Missing or unsafe agent profile registry: $registry"
  PYTHONDONTWRITEBYTECODE=1 python3 "$validator" \
    --profile-dir "$ROOT_DIR/agent-profiles" \
    --registry "$registry" >/dev/null
}

preflight_agent_profile_sync() {
  local action="$1" force="$2" item target_rel src dst
  for item in $(group_agent_profiles codex-agent-profiles); do
    target_rel="$(profile_target "$item")"
    src="$ROOT_DIR/$item"
    dst="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
    [[ -f "$src" && ! -L "$src" ]] || die "Missing or unsafe agent profile source: $item"
    [[ ! -L "$dst" ]] || die "Refusing symlink agent profile target: $dst"
    if [[ -e "$dst" ]] && ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      if [[ "$action" == "install" ]]; then
        die "Refusing to overwrite existing agent profile: $dst"
      fi
      if [[ "$force" -ne 1 ]]; then
        warn "modified agent profile $target_rel; use update --force after reviewing diff"
        diff -u "$src" "$dst" 2>/dev/null | sed -n '1,80p' || true
        return 1
      fi
      safe_backup_path "$dst" >/dev/null
    fi
  done
}

record_agent_profile_state() {
  local item target_rel temp
  mkdir -p "$STATE_DIR"
  temp="$PROFILE_STATE_FILE.tmp.$$"
  : > "$temp"
  for item in $(group_agent_profiles codex-agent-profiles); do
    target_rel="$(profile_target "$item")"
    printf '%s\t%s\n' "$target_rel" "$(file_sha256 "$CODEX_CUSTOM_AGENTS_DIR/$target_rel")" >> "$temp"
  done
  mv "$temp" "$PROFILE_STATE_FILE"
}

report_loop_cli_dependency() {
  if ! python3 -c 'import yaml' >/dev/null 2>&1; then
    warn "Loop Engineering YAML commands require PyYAML in the selected Python environment."
    info "Install explicitly: python3 -m pip install -r $CODEX_SKILLS_DIR/loop-engineering/requirements.txt"
  fi
}

sync_file() {
  local src="$1" dst="$2" label="$3" force="$4"
  if [[ ! -e "$dst" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    ok "new $label"
    return 0
  fi
  if diff -q "$src" "$dst" >/dev/null 2>&1; then
    ok "up-to-date $label"
    return 0
  fi
  if [[ "$force" -eq 1 ]]; then
    local backup
    backup="$(safe_backup_path "$dst")" || return 1
    cp "$dst" "$backup"
    cp "$src" "$dst"
    ok "updated $label (backup: $backup)"
    return 0
  fi
  warn "modified $label; use update --force to overwrite after reviewing diff"
  diff -u "$src" "$dst" 2>/dev/null | sed -n '1,80p' || true
  return 1
}

sync_dir() {
  local src="$1" dst="$2" label="$3" force="$4"
  if [[ ! -e "$dst" ]]; then
    mkdir -p "$dst"
    cp -R "$src"/. "$dst"/
    remove_transient_skill_files "$dst"
    ok "new $label"
    return 0
  fi
  if diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" >/dev/null 2>&1; then
    ok "up-to-date $label"
    return 0
  fi
  if [[ "$force" -eq 1 ]]; then
    local backup
    backup="$(safe_backup_path "$dst")" || return 1
    mkdir -p "$(dirname "$dst")"
    [[ -e "$dst" ]] && cp -R "$dst" "$backup"
    rm -rf "$dst"
    mkdir -p "$dst"
    cp -R "$src"/. "$dst"/
    remove_transient_skill_files "$dst"
    ok "updated $label (backup: $backup)"
    return 0
  fi
  warn "modified $label; use update --force to overwrite after reviewing diff"
  diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" || true
  return 1
}

update_skill() {
  local skill="$1" src dst force="$2"
  src="$ROOT_DIR/skills/$skill"
  dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
  [[ -d "$src" ]] || die "Missing skill source: skills/$skill"
  sync_dir "$src" "$dst" "skill $skill" "$force"
}

update_template() {
  local rel="$1" target_rel src dst force="$2"
  target_rel="$(template_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
  [[ -f "$src" ]] || die "Missing template source: $rel"
  sync_file "$src" "$dst" "template $target_rel" "$force"
}

update_agent_profile() {
  local rel="$1" force="$2" src dst target_rel
  target_rel="$(profile_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
  [[ -f "$src" && ! -L "$src" ]] || die "Missing or unsafe agent profile source: $rel"
  sync_file "$src" "$dst" "agent profile $target_rel" "$force"
}

install_group() {
  local group="$1" item
  info "Installing $group"
  mkdir -p "$CODEX_SKILLS_DIR" "$CODEX_TEMPLATES_DIR"
  for item in $(group_skills "$group"); do
    install_skill "$item"
  done
  for item in $(group_templates "$group"); do
    install_template "$item"
  done
  for item in $(group_agent_profiles "$group"); do
    install_agent_profile "$item"
  done
  if [[ "$group" == "codex-agent-profiles" ]]; then
    record_agent_profile_state
  fi
  [[ "$group" != "codex-delivery-workflow" ]] || report_loop_cli_dependency
  record_state "install" "$group"
}

update_group() {
  local group="$1" force="$2" item
  info "Updating $group"
  mkdir -p "$CODEX_SKILLS_DIR" "$CODEX_TEMPLATES_DIR"
  for item in $(group_skills "$group"); do
    update_skill "$item" "$force" || return 1
  done
  for item in $(group_templates "$group"); do
    update_template "$item" "$force" || return 1
  done
  for item in $(group_agent_profiles "$group"); do
    update_agent_profile "$item" "$force" || return 1
  done
  if [[ "$group" == "codex-agent-profiles" ]]; then
    record_agent_profile_state
  fi
  [[ "$group" != "codex-delivery-workflow" ]] || report_loop_cli_dependency
  record_state "update" "$group"
}

diff_skill() {
  local skill="$1" src dst
  src="$ROOT_DIR/skills/$skill"
  dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
  if [[ ! -d "$dst" ]]; then
    warn "missing installed skill: $skill"
    return 1
  fi
  diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" || return 1
}

diff_template() {
  local rel="$1" target_rel src dst
  target_rel="$(template_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
  if [[ ! -f "$dst" ]]; then
    warn "missing installed template: $target_rel"
    return 1
  fi
  diff -q "$src" "$dst" || return 1
}

diff_agent_profile() {
  local rel="$1" src dst target_rel
  target_rel="$(profile_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
  if [[ ! -f "$dst" ]]; then
    warn "missing installed agent profile: $target_rel"
    return 1
  fi
  diff -q "$src" "$dst" || return 1
}

diff_group() {
  local group="$1" item had_diff=0
  info "Diff $group"
  if [[ "$group" == "codex-agent-profiles" ]]; then
    init_agent_target
  fi
  for item in $(group_skills "$group"); do
    diff_skill "$item" || had_diff=1
  done
  for item in $(group_templates "$group"); do
    diff_template "$item" || had_diff=1
  done
  for item in $(group_agent_profiles "$group"); do
    diff_agent_profile "$item" || had_diff=1
  done
  return "$had_diff"
}

uninstall_group() {
  local group="$1" item target target_rel expected
  info "Uninstalling $group"
  if [[ "$group" == "codex-agent-profiles" ]]; then
    init_agent_target
  fi
  for item in $(group_skills "$group"); do
    target="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$item")" || return 1
    rm -rf "$target"
    ok "removed skill $item"
  done
  for item in $(group_templates "$group"); do
    target_rel="$(template_target "$item")"
    target="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
    rm -f "$target"
    ok "removed template $target_rel"
  done
  if [[ "$group" == "codex-agent-profiles" ]]; then
    for item in $(group_agent_profiles "$group"); do
      target_rel="$(profile_target "$item")"
      target="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
      if [[ -e "$target" ]]; then
        expected=""
        if [[ -f "$PROFILE_STATE_FILE" ]]; then
          expected="$(awk -F '\t' -v name="$target_rel" '$1 == name { print $2; exit }' "$PROFILE_STATE_FILE")"
        fi
        if [[ -n "$expected" ]]; then
          [[ "$(file_sha256 "$target")" == "$expected" ]] || die "Refusing to remove modified agent profile: $target"
        elif ! diff -q "$ROOT_DIR/$item" "$target" >/dev/null 2>&1; then
          die "Refusing to remove agent profile without matching ownership evidence: $target"
        fi
      fi
    done
  fi
  for item in $(group_agent_profiles "$group"); do
    target_rel="$(profile_target "$item")"
    target="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
    if [[ ! -e "$target" ]]; then
      warn "missing installed agent profile: $target_rel"
    else
      rm -f "$target"
      ok "removed agent profile $target_rel"
    fi
  done
  if [[ "$group" == "codex-agent-profiles" ]]; then
    rm -f "$PROFILE_STATE_FILE"
  fi
  record_state "uninstall" "$group"
}

cmd_list() {
  local group
  printf 'codex-dev-skills groups:\n\n'
  for group in $(all_groups); do
    printf '  %s\n    %s\n' "$group" "$(group_description "$group")"
    if [[ -n "$(group_deps "$group")" ]]; then
      printf '    depends_on: %s\n' "$(group_deps "$group")"
    fi
  done
}

cmd_status() {
  printf 'Codex skills target: %s\n' "$CODEX_SKILLS_DIR"
  printf 'Codex templates target: %s\n' "$CODEX_TEMPLATES_DIR"
  printf 'Custom agents target: %s\n' "$CODEX_CUSTOM_AGENTS_DIR"
  printf 'State file: %s\n\n' "$STATE_FILE"
  if [[ -f "$STATE_FILE" ]]; then
    tail -50 "$STATE_FILE"
  else
    printf 'No install state recorded yet.\n'
  fi
}

cmd_manifest() {
  local group item
  for group in $(all_groups); do
    for item in $(group_skills "$group"); do
      printf '%s source: skills/%s\n' "$group" "$item"
    done
    for item in $(group_templates "$group"); do
      printf '%s source: %s\n' "$group" "$item"
    done
    for item in $(group_agent_profiles "$group"); do
      printf '%s source: %s\n' "$group" "$item"
    done
  done
}

run_for_groups() {
  local action="$1" requested="$2" force="${3:-0}" group failed=0 expanded has_agent_profiles=0
  expanded="$(expand_groups "$requested")"
  for group in $expanded; do
    [[ "$group" != "codex-agent-profiles" ]] || has_agent_profiles=1
  done
  if [[ "$has_agent_profiles" -eq 1 && ( "$action" == "install" || "$action" == "update" ) ]]; then
    init_agent_target
    preflight_agent_profile_sync "$action" "$force"
  fi
  for group in $expanded; do
    case "$action" in
      install) install_group "$group" ;;
      update) update_group "$group" "$force" || failed=1 ;;
      diff) diff_group "$group" || failed=1 ;;
    esac
  done
  return "$failed"
}

cmd_uninstall() {
  local requested="" yes=0 group
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all) requested="--all"; shift ;;
      --yes) yes=1; shift ;;
      *) requested="$1"; shift ;;
    esac
  done
  [[ -n "$requested" ]] || die "Usage: ./install.sh uninstall <group> --yes"
  if [[ "$yes" -ne 1 ]]; then
    warn "Uninstall removes installed Codex skills/templates/profiles for the selected group."
    warn "Re-run with --yes after reviewing the target group."
    return 2
  fi
  if [[ "$requested" == "codex-agent-profiles" ]]; then
    uninstall_group "$requested"
  else
    for group in $(expand_groups "$requested"); do
      uninstall_group "$group"
    done
  fi
}

main() {
  local cmd="${1:-}" requested="" force=0 group
  [[ -n "$cmd" ]] || { usage; exit 1; }
  shift || true

  case "$cmd" in
    list) cmd_list; return ;;
    manifest) cmd_manifest; return ;;
    status) cmd_status; return ;;
    -h|--help|help) usage; return ;;
  esac

  case "$cmd" in
    install)
      [[ -n "${1:-}" ]] || die "Usage: ./install.sh install <group>"
      requested="$1" ;;
    update)
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --all) requested="--all"; shift ;;
          --force) force=1; shift ;;
          *) requested="$1"; shift ;;
        esac
      done
      [[ -n "$requested" ]] || die "Usage: ./install.sh update <group> [--force]" ;;
    diff)
      [[ -n "${1:-}" ]] || die "Usage: ./install.sh diff <group>"
      requested="$1" ;;
    uninstall) : ;;
    *) usage; die "Unknown command: $cmd" ;;
  esac

  if [[ "$cmd" == "install" || "$cmd" == "update" ]]; then
    for group in $(expand_groups "$requested"); do
      if [[ "$group" == "codex-agent-profiles" ]]; then
        validate_agent_profile_sources
        break
      fi
    done
  fi

  init_targets

  case "$cmd" in
    install) run_for_groups install "$requested" ;;
    update) run_for_groups update "$requested" "$force" ;;
    diff) run_for_groups diff "$requested" ;;
    uninstall) cmd_uninstall "$@" ;;
  esac
}

main "$@"
