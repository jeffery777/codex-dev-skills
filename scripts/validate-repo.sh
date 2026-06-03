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
    --glob '!docs/migration-from-private-packs.md' \
    --glob '!scripts/validate-repo.sh' >"$TMP_DIR/legacy-hits.txt"; then
    cat "$TMP_DIR/legacy-hits.txt"
    fail "legacy private names found outside migration documentation"
  fi
  ok "legacy private names are confined to migration documentation"
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

check_skill_runtime_labels() {
  local skill missing=0
  while IFS= read -r skill; do
    if ! rg -q '^Runtime compatibility:[[:space:]]*(shared|cli|desktop|plugin-dependent)$' "$skill"; then
      printf '[FAIL] missing runtime compatibility: %s\n' "$skill" >&2
      missing=1
    fi
  done < <(find skills -name SKILL.md -print | sort)
  [[ "$missing" -eq 0 ]] || exit 1
  ok "all skills declare runtime compatibility"
}

main() {
  require_rg
  check_no_provider_terms
  check_sensitive_private_terms
  check_legacy_private_names
  check_catalog_sources
  check_installer_catalog_consistency
  check_skill_runtime_labels
}

main "$@"
