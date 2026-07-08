#!/usr/bin/env bash
# Public repository hygiene checks for codex-dev-skills.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

ok() {
  printf '[OK] %s\n' "$*"
}

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

  local review_pattern
  review_pattern="$(printf '%s|%s|%s|%s|%s|%s' tok'en' sec'ret' au'th' SQL'ite' sess'ion' ca'che')"
  if rg -i "$review_pattern" . >"$TMP_DIR/sensitive-review.txt"; then
    printf '[INFO] sensitive-term review hits; inspect for policy-only usage:\n'
    cat "$TMP_DIR/sensitive-review.txt"
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

check_installer_target_modes() {
  local legacy_manifest agents_manifest
  legacy_manifest="$TMP_DIR/installer-legacy-manifest.txt"
  agents_manifest="$TMP_DIR/installer-agents-manifest.txt"

  ./install.sh help > "$TMP_DIR/install-help.txt"
  rg -F -q 'CODEX_DEV_SKILLS_TARGET=agents' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document CODEX_DEV_SKILLS_TARGET=agents"
  rg -F -q '~/.codex/skills/<skill>/' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the legacy skills target"
  rg -F -q '~/.agents/skills/<skill>/' "$TMP_DIR/install-help.txt" \
    || fail "installer help must document the agents skills target"

  ./install.sh manifest | sort -u > "$legacy_manifest"
  CODEX_DEV_SKILLS_TARGET=agents ./install.sh manifest | sort -u > "$agents_manifest"
  if ! diff -u "$legacy_manifest" "$agents_manifest"; then
    fail "installer manifests must not differ by target mode"
  fi
  if CODEX_DEV_SKILLS_TARGET=invalid ./install.sh help >"$TMP_DIR/install-invalid.out" 2>"$TMP_DIR/install-invalid.err"; then
    fail "invalid CODEX_DEV_SKILLS_TARGET must fail closed"
  fi
  ok "installer target modes are documented and fail closed"
}

check_installer_version() {
  local current_release_version installer_version
  current_release_version="$(sed -n 's/.*current v\([0-9][0-9.]*\) release notes.*/\1/p' README.md | head -n 1)"
  installer_version="$(sed -n 's/^VERSION="\([^"]*\)"/\1/p' install.sh | head -n 1)"
  [[ -n "$current_release_version" ]] || fail "README must reference current release notes"
  [[ -n "$installer_version" ]] || fail "install.sh must declare VERSION"
  if [[ "$installer_version" != "$current_release_version" ]]; then
    fail "install.sh VERSION ($installer_version) must match current release notes version ($current_release_version)"
  fi
  ok "installer version matches current release notes"
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
  python3 scripts/validate-loop-ledger.py
}

main() {
  require_rg
  check_no_provider_terms
  check_sensitive_private_terms
  check_legacy_private_names
  check_catalog_sources
  check_installer_catalog_consistency
  check_installer_target_modes
  check_installer_version
  check_skill_metadata
  check_loop_ledger
}

main "$@"
