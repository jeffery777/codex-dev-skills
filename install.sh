#!/usr/bin/env bash
# Codex-only installer for codex-dev-skills.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_BASE="${XDG_STATE_HOME:-$HOME/.local/state}"
STATE_DIR="$STATE_BASE/codex-dev-skills"
STATE_FILE="$STATE_DIR/installed.jsonl"
MANAGED_BACKUP_ROOT="$STATE_DIR/backups/v1"
TRANSACTION_LOCK_DIR=""
TRANSACTION_LOCK_HELD=0
TRANSACTION_APPLY_ACTIVE=0
PROFILE_STATE_FILE=""
DEFAULT_CODEX_LEGACY_SKILLS_DIR="$HOME/.codex/skills"
DEFAULT_CODEX_AGENTS_SKILLS_DIR="$HOME/.agents/skills"
DEFAULT_CODEX_TEMPLATES_DIR="$HOME/.codex/templates"
DEFAULT_CODEX_CUSTOM_AGENTS_DIR="$HOME/.codex/agents"
CODEX_DEV_SKILLS_TARGET="${CODEX_DEV_SKILLS_TARGET:-agents}"
CODEX_TEMPLATES_DIR="${CODEX_TEMPLATES_DIR:-$DEFAULT_CODEX_TEMPLATES_DIR}"
CODEX_CUSTOM_AGENTS_DIR="${CODEX_CUSTOM_AGENTS_DIR:-$DEFAULT_CODEX_CUSTOM_AGENTS_DIR}"
VERSION="0.21.0"

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
  codex-cli-session-handoff
  desktop-delivery-workflow
  codex-agent-profiles (explicit opt-in; excluded from --all)

Targets:
  Codex skills:    ~/.agents/skills/<skill>/ by default
                   ~/.codex/skills/<skill>/ when CODEX_DEV_SKILLS_TARGET=legacy
  Codex templates: ~/.codex/templates/...
  Custom agents:   ~/.codex/agents/<profile>.toml by default
                   Set CODEX_CUSTOM_AGENTS_DIR=<trusted-project>/.codex/agents with
                   CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES for project adoption.

This installer never overwrites ~/.codex/AGENTS.md.
Custom CODEX_SKILLS_DIR / CODEX_TEMPLATES_DIR / CODEX_CUSTOM_AGENTS_DIR values require CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES.
Existing installs are never moved or removed automatically.
If the same skill exists in both standard discovery paths, resolve the duplicate
or use CODEX_DEV_SKILLS_TARGET=legacy to maintain an existing legacy install.
If the codex-dev-skills plugin is installed, remove either the plugin or the
filesystem installation before using install/update. The installer checks the
documented `codex plugin list --json` surface when the active CLI supports it.
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

reject_unsafe_parent_components() {
  local path parent component current
  local -a parts=()
  path="$(absolute_path "$1")"
  parent="$(dirname "${path%/}")"
  current=""
  IFS='/' read -r -a parts <<< "$parent"
  for component in "${parts[@]}"; do
    [[ -z "$component" ]] && continue
    current="$current/$component"
    [[ ! -L "$current" ]] || die "Refusing symlink path component: $current"
    if [[ -e "$current" && ! -d "$current" ]]; then
      die "Refusing non-directory path component: $current"
    fi
  done
}

validate_root_without_create() {
  local raw="$1" default_raw="$2" label="$3" abs default_abs real_abs
  abs="$(absolute_path "$raw")"
  default_abs="$(absolute_path "$default_raw")"
  reject_symlink_components "$abs"
  real_abs="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$abs")" || return 1
  default_abs="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$default_abs")" || return 1
  if [[ "$real_abs" != "$default_abs" ]]; then
    if [[ "${CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS:-}" != "YES" ]]; then
      die "$label override requires CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES: $raw"
    fi
    reject_suspicious_root_path "$raw" "$label"
    reject_custom_root "$real_abs" "$label"
  fi
  if [[ -e "$real_abs" && ! -d "$real_abs" ]]; then
    die "$label target root is not a directory: $real_abs"
  fi
  printf '%s\n' "$real_abs"
}

canonicalize_root() {
  local raw="$1" default_raw="$2" label="$3" real_abs
  real_abs="$(validate_root_without_create "$raw" "$default_raw" "$label")" || return 1
  ensure_owned_safe_directory "$real_abs" "$label target root" || return 1
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

preflight_targets() {
  CODEX_SKILLS_DIR="$(validate_root_without_create "$CODEX_SKILLS_DIR" "$DEFAULT_CODEX_SKILLS_DIR" "CODEX_SKILLS_DIR")" || return 1
  CODEX_TEMPLATES_DIR="$(validate_root_without_create "$CODEX_TEMPLATES_DIR" "$DEFAULT_CODEX_TEMPLATES_DIR" "CODEX_TEMPLATES_DIR")" || return 1
}

init_agent_target() {
  CODEX_CUSTOM_AGENTS_DIR="$(canonicalize_root "$CODEX_CUSTOM_AGENTS_DIR" "$DEFAULT_CODEX_CUSTOM_AGENTS_DIR" "CODEX_CUSTOM_AGENTS_DIR")" || return 1
  PROFILE_STATE_FILE="$STATE_DIR/agent-profile-$(python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' "$CODEX_CUSTOM_AGENTS_DIR").tsv"
}

preflight_agent_target() {
  CODEX_CUSTOM_AGENTS_DIR="$(validate_root_without_create "$CODEX_CUSTOM_AGENTS_DIR" "$DEFAULT_CODEX_CUSTOM_AGENTS_DIR" "CODEX_CUSTOM_AGENTS_DIR")" || return 1
  PROFILE_STATE_FILE="$STATE_DIR/agent-profile-$(python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' "$CODEX_CUSTOM_AGENTS_DIR").tsv"
}

alternate_standard_skills_root() {
  case "$CODEX_SKILLS_DIR" in
    "$DEFAULT_CODEX_AGENTS_SKILLS_DIR") printf '%s\n' "$DEFAULT_CODEX_LEGACY_SKILLS_DIR" ;;
    "$DEFAULT_CODEX_LEGACY_SKILLS_DIR") printf '%s\n' "$DEFAULT_CODEX_AGENTS_SKILLS_DIR" ;;
    *) return 1 ;;
  esac
}

preflight_cross_root_skill_collisions() {
  local requested="$1" alternate group skill collision=0
  alternate="$(alternate_standard_skills_root)" || return 0
  for group in $(expand_groups "$requested"); do
    for skill in $(group_skills "$group"); do
      if [[ -e "$alternate/$skill" || -L "$alternate/$skill" ]]; then
        warn "skill '$skill' also exists in alternate discovery root: $alternate/$skill"
        collision=1
      fi
    done
  done
  if [[ "$collision" -eq 1 ]]; then
    die "Refusing to create duplicate skill discovery entries across ~/.agents/skills and ~/.codex/skills. Existing installs are not moved or removed automatically."
  fi
}

resolve_codex_cli() {
  local candidate="${CODEX_CLI:-}" resolved
  if [[ -z "$candidate" ]]; then
    candidate="$(command -v codex 2>/dev/null || true)"
  fi
  [[ -n "$candidate" ]] || return 1
  case "$candidate" in
    /*) ;;
    *) warn "Ignoring non-absolute CODEX_CLI path: $candidate"; return 1 ;;
  esac
  resolved="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$candidate")" || return 1
  [[ "$resolved" == /* && -f "$resolved" && -x "$resolved" ]] || {
    warn "Ignoring unsafe or unavailable Codex CLI executable: $candidate"
    return 1
  }
  printf '%s\n' "$resolved"
}

preflight_plugin_distribution_collision() {
  local codex_cli payload parse_status
  codex_cli="$(resolve_codex_cli)" || {
    warn "Codex CLI unavailable; plugin-install collision could not be checked. Use only one distribution path."
    return 0
  }
  if ! payload="$(umask 077; "$codex_cli" plugin list --json 2>/dev/null)"; then
    warn "Active Codex CLI does not expose a readable plugin list; use only one distribution path."
    return 0
  fi
  if printf '%s' "$payload" | python3 -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, OSError):
    raise SystemExit(2)
installed = payload.get("installed") if isinstance(payload, dict) else None
if not isinstance(installed, list):
    raise SystemExit(2)
collision = any(
    isinstance(item, dict)
    and item.get("name") == "codex-dev-skills"
    and item.get("installed", True) is not False
    for item in installed
)
raise SystemExit(0 if collision else 1)
'; then
    die "Refusing filesystem installation while the codex-dev-skills plugin is installed. Remove one distribution path first."
  else
    parse_status=$?
    if [[ "$parse_status" -ne 1 ]]; then
      warn "Codex plugin list returned an unsupported JSON shape; use only one distribution path."
    fi
  fi
}

report_cross_root_skill_collisions() {
  local alternate group skill seen="" found=0
  alternate="$(alternate_standard_skills_root)" || {
    printf 'Cross-target skill collisions: not checked for custom skills target\n'
    return
  }
  for group in $(all_groups); do
    for skill in $(group_skills "$group"); do
      case " $seen " in *" $skill "*) continue ;; esac
      seen="$seen $skill"
      if [[ -e "$alternate/$skill" || -L "$alternate/$skill" ]]; then
        if [[ -e "$CODEX_SKILLS_DIR/$skill" || -L "$CODEX_SKILLS_DIR/$skill" ]]; then
          printf 'Cross-target skill collision: %s\n' "$skill"
        else
          printf 'Alternate-root managed skill detected: %s\n' "$skill"
        fi
        found=1
      fi
    done
  done
  [[ "$found" -eq 1 ]] || printf 'Alternate-root managed skills: none detected\n'
}

safe_path_under_root() {
  local root="$1" rel="$2" path
  reject_suspicious_relpath "$rel"
  path="$root/$rel"
  reject_symlink_components "$path"
  reject_unsafe_parent_components "$path"
  printf '%s\n' "$path"
}

path_is_within() {
  local path="${1%/}" root="${2%/}"
  [[ "$path" == "$root" || "$path" == "$root/"* ]]
}

sha256_text() {
  python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' "$1"
}

safe_backup_path() {
  local target_root="$1" kind="$2" rel="$3" backup_root digest backup
  reject_suspicious_relpath "$rel"
  digest="$(sha256_text "$target_root")" || return 1
  backup_root="$(absolute_path "$MANAGED_BACKUP_ROOT")/$digest/$kind"
  backup="$backup_root/$rel.bak"
  reject_symlink_components "$backup"
  reject_unsafe_parent_components "$backup"
  path_is_within "$backup" "$backup_root" || die "Managed backup path escapes its artifact root: $backup"
  [[ ! -e "$backup" && ! -L "$backup" ]] || die "Refusing to overwrite existing managed backup path: $backup"
  printf '%s\n' "$backup"
}

validate_owned_safe_directory() {
  local path="$1" label="$2"
  [[ -d "$path" && ! -L "$path" ]] || die "$label is not a safe directory: $path"
  python3 - "$path" "$label" <<'PY'
import os
import stat
import sys

path, label = sys.argv[1:]
st = os.stat(path, follow_symlinks=False)
if st.st_uid != os.getuid():
    print(f"[ERROR] {label} is not owned by the current user: {path}", file=sys.stderr)
    raise SystemExit(1)
if stat.S_IMODE(st.st_mode) & 0o022:
    print(f"[ERROR] {label} is group/world writable: {path}", file=sys.stderr)
    raise SystemExit(1)
PY
}

validate_mutable_directory_chain() {
  local path="$1" label="$2"
  python3 - "$path" "$label" <<'PY'
import os
import stat
import sys

path, label = os.path.abspath(sys.argv[1]), sys.argv[2]
current = os.path.sep
for component in path.split(os.path.sep):
    if not component:
        continue
    current = os.path.join(current, component)
    st = os.lstat(current)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        print(f"[ERROR] {label} has an unsafe intermediate component: {current}", file=sys.stderr)
        raise SystemExit(1)
    mode = stat.S_IMODE(st.st_mode)
    trusted_sticky_root = st.st_uid == 0 and bool(mode & stat.S_ISVTX)
    if st.st_uid not in (0, os.getuid()):
        print(f"[ERROR] {label} has an untrusted owner on intermediate component: {current}", file=sys.stderr)
        raise SystemExit(1)
    if mode & 0o022 and not trusted_sticky_root:
        print(f"[ERROR] {label} has a group/world-writable intermediate component: {current}", file=sys.stderr)
        raise SystemExit(1)
PY
}

checked_validator() {
  ( "$@" )
}

ensure_owned_safe_directory() {
  local path="$1" label="$2" ancestor current component index
  local -a missing=()
  path="$(absolute_path "$path")"
  checked_validator reject_symlink_components "$path" || return 1
  checked_validator reject_unsafe_parent_components "$path" || return 1
  ancestor="$path"
  while [[ ! -e "$ancestor" && ! -L "$ancestor" ]]; do
    missing[${#missing[@]}]="$(basename "$ancestor")"
    ancestor="$(dirname "$ancestor")"
  done
  checked_validator validate_mutable_directory_chain "$ancestor" "$label existing ancestor" || return 1
  current="$ancestor"
  for ((index=${#missing[@]}-1; index>=0; index--)); do
    component="${missing[$index]}"
    current="$current/$component"
    (umask 077; mkdir -m 700 "$current") || return 1
    checked_validator validate_mutable_directory_chain "$current" "$label created path" || return 1
    checked_validator validate_owned_safe_directory "$current" "$label created directory" || return 1
  done
  checked_validator validate_mutable_directory_chain "$path" "$label" || return 1
  checked_validator validate_owned_safe_directory "$path" "$label" || return 1
}

validate_existing_artifact() {
  local path="$1" expected="$2" label="$3"
  [[ ! -L "$path" ]] || die "Refusing symlink $label target: $path"
  [[ -e "$path" ]] || return 0
  case "$expected" in
    directory) [[ -d "$path" ]] || die "$label target is not a directory: $path" ;;
    file) [[ -f "$path" ]] || die "$label target is not a regular file: $path" ;;
    *) die "Internal error: unsupported artifact type: $expected" ;;
  esac
  python3 - "$path" "$label" <<'PY'
import os
import stat
import sys

path, label = sys.argv[1:]
st = os.stat(path, follow_symlinks=False)
if st.st_uid != os.getuid():
    print(f"[ERROR] {label} target is not owned by the current user: {path}", file=sys.stderr)
    raise SystemExit(1)
if stat.S_IMODE(st.st_mode) & 0o022:
    print(f"[ERROR] {label} target is group/world writable: {path}", file=sys.stderr)
    raise SystemExit(1)
if stat.S_ISREG(st.st_mode) and st.st_nlink != 1:
    print(f"[ERROR] {label} target is a multiply-linked regular file: {path}", file=sys.stderr)
    raise SystemExit(1)
if stat.S_ISDIR(st.st_mode):
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            child = os.path.join(root, name)
            child_st = os.lstat(child)
            if stat.S_ISLNK(child_st.st_mode):
                print(f"[ERROR] {label} target tree contains a symlink: {child}", file=sys.stderr)
                raise SystemExit(1)
            if not (stat.S_ISDIR(child_st.st_mode) or stat.S_ISREG(child_st.st_mode)):
                print(f"[ERROR] {label} target tree contains a special file: {child}", file=sys.stderr)
                raise SystemExit(1)
            if child_st.st_uid != os.getuid():
                print(f"[ERROR] {label} target tree contains an entry not owned by the current user: {child}", file=sys.stderr)
                raise SystemExit(1)
            if stat.S_IMODE(child_st.st_mode) & 0o022:
                print(f"[ERROR] {label} target tree contains a group/world-writable entry: {child}", file=sys.stderr)
                raise SystemExit(1)
            if stat.S_ISREG(child_st.st_mode) and child_st.st_nlink != 1:
                print(f"[ERROR] {label} target tree contains a multiply-linked regular file: {child}", file=sys.stderr)
                raise SystemExit(1)
PY
}

validate_receipt_writable() {
  local path="$1" label="$2"
  python3 - "$path" "$label" <<'PY'
import os
import stat
import sys

path, label = sys.argv[1:]
st = os.stat(path, follow_symlinks=False)
if not stat.S_ISREG(st.st_mode):
    print(f"[ERROR] {label} is not a regular file: {path}", file=sys.stderr)
    raise SystemExit(1)
if not stat.S_IMODE(st.st_mode) & stat.S_IWUSR:
    print(f"[ERROR] {label} is not writable by its owner: {path}", file=sys.stderr)
    raise SystemExit(1)
protected_flags = 0
for flag_name in ("UF_IMMUTABLE", "UF_APPEND", "SF_IMMUTABLE", "SF_APPEND"):
    protected_flags |= getattr(stat, flag_name, 0)
if getattr(st, "st_flags", 0) & protected_flags:
    print(f"[ERROR] {label} has immutable or append-only file flags: {path}", file=sys.stderr)
    raise SystemExit(1)
flags = os.O_WRONLY | os.O_APPEND
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
try:
    fd = os.open(path, flags)
except OSError as exc:
    print(f"[ERROR] {label} cannot be opened for append: {path}: {exc}", file=sys.stderr)
    raise SystemExit(1)
try:
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
        print(f"[ERROR] {label} changed during writable preflight: {path}", file=sys.stderr)
        raise SystemExit(1)
    if sys.platform.startswith("linux"):
        import ctypes
        import fcntl
        import struct

        # Linux UAPI: FS_IOC_GETFLAGS is _IOR('f', 1, long), using the
        # asm-generic ioctl layout; the encoded size follows the process ABI.
        long_size = ctypes.sizeof(ctypes.c_long)
        getflags_request = (2 << 30) | (ord("f") << 8) | 1 | (long_size << 16)
        raw_flags = bytearray(long_size)
        try:
            fcntl.ioctl(fd, getflags_request, raw_flags, True)
        except OSError as exc:
            # Unsupported filesystems and a mismatched ioctl ABI are not
            # distinguishable here, so neither can safely fall back.
            print(f"[ERROR] {label} file flags cannot be inspected: {path}: {exc}", file=sys.stderr)
            raise SystemExit(1)
        else:
            # The ioctl request encodes sizeof(long), but Linux writes the
            # unsigned-int payload into the first four bytes of that buffer.
            linux_flags = struct.unpack_from("=I", raw_flags)[0]
            # Linux UAPI linux/fs.h inode flags.
            fs_immutable_fl = 0x00000010
            fs_append_fl = 0x00000020
            if linux_flags & (fs_immutable_fl | fs_append_fl):
                print(f"[ERROR] {label} has immutable or append-only inode flags: {path}", file=sys.stderr)
                raise SystemExit(1)
finally:
    os.close(fd)
PY
}

validate_receipt_parent_writable() {
  local path="$1" label="$2"
  python3 - "$path" "$label" <<'PY'
import os
import stat
import sys

path, label = sys.argv[1:]
st = os.stat(path, follow_symlinks=False)
mode = stat.S_IMODE(st.st_mode)
if not stat.S_ISDIR(st.st_mode):
    print(f"[ERROR] {label} is not a directory: {path}", file=sys.stderr)
    raise SystemExit(1)
if not mode & stat.S_IWUSR or not mode & stat.S_IXUSR:
    print(f"[ERROR] {label} is not writable and searchable by its owner: {path}", file=sys.stderr)
    raise SystemExit(1)
PY
}

preflight_nonforce_receipt() {
  local path="$1" label="$2"
  checked_validator reject_symlink_components "$path" || return 1
  checked_validator reject_unsafe_parent_components "$path" || return 1
  path_is_within "$path" "$STATE_DIR" || die "$label escapes the installer state directory: $path"
  if [[ -e "$path" || -L "$path" ]]; then
    checked_validator validate_existing_artifact "$path" file "$label" || return 1
    checked_validator validate_receipt_writable "$path" "$label" || return 1
  fi
}

preflight_nonforce_state() {
  local requested="$1" group probe="" renamed_probe="" has_profiles=0
  ensure_owned_safe_directory "$STATE_DIR" "Installer state directory" || return 1
  checked_validator validate_receipt_parent_writable "$STATE_DIR" "Installer state directory" || return 1
  preflight_nonforce_receipt "$STATE_FILE" "installer state receipt" || return 1
  for group in $(expand_groups "$requested"); do
    if [[ "$group" == "codex-agent-profiles" ]]; then
      has_profiles=1
      break
    fi
  done
  if [[ "$has_profiles" -eq 1 ]]; then
    [[ -n "$PROFILE_STATE_FILE" ]] || die "Internal error: agent profile state receipt path was not initialized"
    preflight_nonforce_receipt "$PROFILE_STATE_FILE" "agent profile state receipt" || return 1
  fi
  probe="$(umask 077; mktemp "$STATE_DIR/.codex-dev-skills.state-preflight.XXXXXX")" || return 1
  if ! checked_validator validate_existing_artifact "$probe" file "installer state write probe"; then
    rm -f "$probe" || true
    return 1
  fi
  renamed_probe="$probe.renamed"
  if [[ -e "$renamed_probe" || -L "$renamed_probe" ]]; then
    rm -f "$probe" || true
    warn "Refusing occupied installer state rename probe path: $renamed_probe"
    return 1
  fi
  if ! mv "$probe" "$renamed_probe"; then
    rm -f "$probe" "$renamed_probe" || true
    return 1
  fi
  if ! checked_validator validate_existing_artifact "$renamed_probe" file "installer state rename probe"; then
    rm -f "$renamed_probe" || true
    return 1
  fi
  rm -f "$renamed_probe" || return 1
}

validate_source_artifact() {
  local path="$1" expected="$2" label="$3"
  [[ ! -L "$path" ]] || die "Source is a symlink for $label: $path"
  case "$expected" in
    directory) [[ -d "$path" ]] || die "Missing or unsafe source for $label: $path" ;;
    file) [[ -f "$path" ]] || die "Missing or unsafe source for $label: $path" ;;
  esac
  python3 - "$path" "$expected" "$label" <<'PY'
import os
import stat
import sys

path, expected, label = sys.argv[1:]
paths = [path]
if expected == "directory":
    for root, dirs, files in os.walk(path, followlinks=False):
        paths.extend(os.path.join(root, name) for name in dirs + files)
for candidate in paths:
    candidate_st = os.lstat(candidate)
    mode = candidate_st.st_mode
    if stat.S_ISLNK(mode):
        print(f"[ERROR] Source tree for {label} contains a symlink: {candidate}", file=sys.stderr)
        raise SystemExit(1)
    if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
        print(f"[ERROR] Source tree for {label} contains a special file: {candidate}", file=sys.stderr)
        raise SystemExit(1)
    if stat.S_ISREG(mode) and candidate_st.st_nlink != 1:
        print(f"[ERROR] Source tree for {label} contains a multiply-linked regular file: {candidate}", file=sys.stderr)
        raise SystemExit(1)
PY
}

path_device() {
  python3 -c 'import os, sys; print(os.stat(sys.argv[1], follow_symlinks=False).st_dev)' "$1"
}

validate_managed_backup_root() {
  local raw_root canonical_root repo skills templates profiles standard_agents standard_legacy candidate
  raw_root="$(absolute_path "$MANAGED_BACKUP_ROOT")"
  checked_validator reject_symlink_components "$raw_root" || return 1
  checked_validator reject_unsafe_parent_components "$raw_root" || return 1
  repo="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$ROOT_DIR")" || return 1
  skills="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$CODEX_SKILLS_DIR")" || return 1
  templates="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$CODEX_TEMPLATES_DIR")" || return 1
  profiles="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$CODEX_CUSTOM_AGENTS_DIR")" || return 1
  standard_agents="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$DEFAULT_CODEX_AGENTS_SKILLS_DIR")" || return 1
  standard_legacy="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$DEFAULT_CODEX_LEGACY_SKILLS_DIR")" || return 1
  canonical_root="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$raw_root")" || return 1
  for candidate in "$repo" "$skills" "$templates" "$profiles" "$standard_agents" "$standard_legacy"; do
    if path_is_within "$canonical_root" "$candidate" || path_is_within "$candidate" "$canonical_root"; then
      die "Managed backup root overlaps a protected repository or target boundary: $raw_root and $candidate"
    fi
  done
  if [[ -e "$raw_root" && ! -d "$raw_root" ]]; then
    die "Managed backup root is not a directory: $raw_root"
  fi
  printf '%s\n' "$raw_root"
}

init_managed_backup_root() {
  local root state_base state backups
  root="$(validate_managed_backup_root)" || return 1
  state_base="$(absolute_path "$STATE_BASE")"
  state="$(absolute_path "$STATE_DIR")"
  backups="$(dirname "$root")"
  ensure_owned_safe_directory "$state_base" "State base directory" || return 1
  ensure_owned_safe_directory "$state" "Installer state directory" || return 1
  ensure_owned_safe_directory "$backups" "Managed backups directory" || return 1
  ensure_owned_safe_directory "$root" "Managed backup root" || return 1
  MANAGED_BACKUP_ROOT="$root"
}

release_transaction_lock() {
  [[ "$TRANSACTION_LOCK_HELD" -eq 1 ]] || return 0
  if ! rm -f "$TRANSACTION_LOCK_DIR/owner" || ! rmdir "$TRANSACTION_LOCK_DIR"; then
    warn "Failed to release managed backup transaction lock: $TRANSACTION_LOCK_DIR"
    return 1
  fi
  TRANSACTION_LOCK_HELD=0
  return 0
}

handle_transaction_signal() {
  local status="$1"
  trap '' INT HUP TERM
  if [[ "$TRANSACTION_APPLY_ACTIVE" -eq 1 ]]; then
    if [[ "${#RX_STATUS[@]}" -gt 0 ]]; then
      rollback_force_update_receipts "$(( ${#RX_STATUS[@]} - 1 ))" || true
    fi
    if [[ "${#TX_STATUS[@]}" -gt 0 ]]; then
      rollback_force_update_transaction "$(( ${#TX_STATUS[@]} - 1 ))" || true
    fi
  fi
  cleanup_transaction_staging || true
  cleanup_receipt_staging || true
  release_transaction_lock || true
  exit "$status"
}

acquire_transaction_lock() {
  init_managed_backup_root || return 1
  TRANSACTION_LOCK_DIR="$MANAGED_BACKUP_ROOT/.transaction.lock"
  if ! mkdir -m 700 "$TRANSACTION_LOCK_DIR"; then
    warn "Managed backup transaction lock already exists; inspect and remove it manually only after confirming no installer is active: $TRANSACTION_LOCK_DIR"
    return 1
  fi
  TRANSACTION_LOCK_HELD=1
  trap 'release_transaction_lock' EXIT
  trap 'handle_transaction_signal 130' INT
  trap 'handle_transaction_signal 129' HUP
  trap 'handle_transaction_signal 143' TERM
  if ! (umask 077; printf 'pid=%s\nstarted_at=%s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$TRANSACTION_LOCK_DIR/owner"); then
    warn "Failed to record managed backup transaction lock ownership: $TRANSACTION_LOCK_DIR"
    release_transaction_lock || true
    return 1
  fi
}

preflight_filesystem_sync() {
  local action="$1" requested="$2" force="$3"
  local group skill rel target_rel src dst collision=0 backup
  for group in $(expand_groups "$requested"); do
    for skill in $(group_skills "$group"); do
      src="$ROOT_DIR/skills/$skill"
      [[ -d "$src" && ! -L "$src" ]] || die "Missing or unsafe skill source: skills/$skill"
      dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
      validate_existing_artifact "$dst" directory "skill $skill"
      if [[ -e "$dst" || -L "$dst" ]]; then
        if [[ ! -d "$dst" || -L "$dst" ]] ||
           ! diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" >/dev/null 2>&1; then
          warn "existing skill differs from repository source: $dst"
          collision=1
          if [[ "$action" == "update" && "$force" -eq 1 ]]; then
            backup="$(safe_backup_path "$CODEX_SKILLS_DIR" skills "$skill")" || return 1
            [[ ! -e "$backup" && ! -L "$backup" ]] || die "Refusing to overwrite existing backup path: $backup"
          fi
        fi
      fi
    done
    for rel in $(group_templates "$group"); do
      target_rel="$(template_target "$rel")"
      src="$ROOT_DIR/$rel"
      [[ -f "$src" && ! -L "$src" ]] || die "Missing or unsafe template source: $rel"
      dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
      validate_existing_artifact "$dst" file "template $target_rel"
      if [[ -e "$dst" || -L "$dst" ]]; then
        if [[ ! -f "$dst" || -L "$dst" ]] || ! diff -q "$src" "$dst" >/dev/null 2>&1; then
          warn "existing template differs from repository source: $dst"
          collision=1
          if [[ "$action" == "update" && "$force" -eq 1 ]]; then
            backup="$(safe_backup_path "$CODEX_TEMPLATES_DIR" templates "$target_rel")" || return 1
            [[ ! -e "$backup" && ! -L "$backup" ]] || die "Refusing to overwrite existing backup path: $backup"
          fi
        fi
      fi
    done
  done
  if [[ "$collision" -eq 1 ]]; then
    if [[ "$action" == "install" ]]; then
      die "Refusing to overwrite differing installed or imported artifacts. Review the source, then use update --force only for a managed filesystem installation."
    fi
    if [[ "$force" -ne 1 ]]; then
      die "Refusing a partial update while installed artifacts differ. Review the source, then use update --force only for a managed filesystem installation."
    fi
  fi
}

all_groups() {
  printf '%s\n' \
    shared-review-gates \
    codex-review-workflow \
    codex-delivery-workflow \
    codex-cli-session-handoff \
    desktop-delivery-workflow \
    codex-agent-profiles
}

default_groups() {
  printf '%s\n' \
    shared-review-gates \
    codex-review-workflow \
    codex-delivery-workflow \
    codex-cli-session-handoff \
    desktop-delivery-workflow
}

group_exists() {
  case "$1" in
    shared-review-gates|codex-review-workflow|codex-delivery-workflow|codex-cli-session-handoff|desktop-delivery-workflow|codex-agent-profiles) return 0 ;;
    codex-dev-skills) return 0 ;;
    *) return 1 ;;
  esac
}

group_description() {
  case "$1" in
    shared-review-gates) echo "Shared review gates, closure triage, safety policies, and orchestration templates." ;;
    codex-review-workflow) echo "Routine and deep code, docs, and merge review workflows." ;;
    codex-delivery-workflow) echo "Shared loop engineering, planning, bounded implementation, docs update, and delegated delivery workflows." ;;
    codex-cli-session-handoff) echo "CLI-only non-interactive start/resume/fork/fresh-continuation plus manual interactive-fork, agents-dashboard, and argv-safe UUID queue guidance over the shared delivery workflow." ;;
    desktop-delivery-workflow) echo "Three active Codex Desktop entry/control-plane adapters plus deprecated shared-gate compatibility aliases." ;;
    codex-agent-profiles) echo "Opt-in Loop Engineering V2a custom-agent runtime profiles." ;;
    codex-dev-skills) echo "Alias for all groups." ;;
  esac
}

group_deps() {
  case "$1" in
    shared-review-gates) : ;;
    codex-review-workflow) echo "shared-review-gates" ;;
    codex-delivery-workflow) echo "shared-review-gates" ;;
    codex-cli-session-handoff) echo "shared-review-gates codex-delivery-workflow" ;;
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
    codex-cli-session-handoff)
      printf '%s\n' cli-session-handoff ;;
    desktop-delivery-workflow)
      printf '%s\n' desktop-project-delivery desktop-thread-delegation desktop-sidebar-organization desktop-spec-plan-gate desktop-implementation-gate desktop-pr-merge-gate ;;
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
        agent-profiles/loop_v2a_senior_worker.toml \
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
        policies/code-mode-tool-orchestration-policy.md \
        policies/context-continuity-policy.md \
        policies/delivery-drift-control-policy.md \
        policies/exact-head-merge-review-contract.md \
        policies/github-control-plane-policy.md \
        policies/human-gate-policy.md \
        policies/model-selection-policy.md \
        policies/multi-agent-integration-policy.md \
        policies/project-agent-knowledge-policy.md \
        policies/projectspec-alignment-policy.md \
        policies/release-state-contract.md \
        policies/reusable-workflow-contract.md \
        policies/review-artifact-policy.md \
        policies/runtime-compatibility-policy.md \
        policies/security-review-escalation-policy.md \
        scripts/validate-exact-head-merge-review.py \
        scripts/collect-exact-head-merge-readiness.py \
        templates/orchestration/agent-task-brief.template.md \
        templates/orchestration/agent-routing-integration.template.yaml \
        templates/orchestration/closure-triage-overlay.template.yaml \
        templates/orchestration/current-task-summary.template.md \
        templates/orchestration/context-continuity.template.yaml \
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
        templates/hooks/gitnexus-v2c-b/hooks.json.template \
        templates/hooks/gitnexus-v2c-b/config.json.template \
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

selected_uninstall_groups() {
  local requested="$1"
  if [[ "$requested" == "--all" || "$requested" == "codex-dev-skills" ]]; then
    default_groups
    return
  fi
  ensure_group "$requested"
  printf '%s\n' "$requested"
}

group_has_installed_skill() {
  local root="$1" group="$2" skill
  for skill in $(group_skills "$group"); do
    if [[ -e "$root/$skill" || -L "$root/$skill" ]]; then
      return 0
    fi
  done
  return 1
}

agent_profile_state_exists() {
  local state
  [[ -d "$STATE_DIR" ]] || return 1
  for state in "$STATE_DIR"/agent-profile-*.tsv; do
    if [[ -f "$state" && -s "$state" ]]; then
      return 0
    fi
  done
  return 1
}

group_has_installed_artifact() {
  local group="$1" profile
  if group_has_installed_skill "$CODEX_SKILLS_DIR" "$group"; then
    return 0
  fi
  if [[ "$group" == "codex-agent-profiles" ]] &&
     agent_profile_state_exists; then
    return 0
  fi
  for profile in $(group_agent_profiles "$group"); do
    if [[ -e "$CODEX_CUSTOM_AGENTS_DIR/$(profile_target "$profile")" ]]; then
      return 0
    fi
  done
  return 1
}

group_depends_on() {
  local group="$1" dependency="$2" candidate
  [[ "$group" != "$dependency" ]] || return 0
  for candidate in $(group_deps "$group"); do
    [[ "$candidate" != "$dependency" ]] || return 0
  done
  return 1
}

preflight_uninstall_cross_root() {
  local requested="$1" alternate expanded group alternate_group mismatch=0 protected=0
  alternate="$(alternate_standard_skills_root)" || return 0
  expanded="$(selected_uninstall_groups "$requested")"

  for group in $expanded; do
    if ! group_has_installed_skill "$CODEX_SKILLS_DIR" "$group" &&
       group_has_installed_skill "$alternate" "$group"; then
      warn "selected target has no installed '$group' skills, but the alternate discovery root does: $alternate"
      mismatch=1
    fi
  done
  if [[ "$mismatch" -eq 1 ]]; then
    die "Refusing uninstall from the wrong skill target. Re-run with CODEX_DEV_SKILLS_TARGET=legacy when uninstalling a legacy installation."
  fi

  for group in $expanded; do
    [[ -n "$(group_templates "$group")" ]] || continue
    for alternate_group in $(all_groups); do
      if group_depends_on "$alternate_group" "$group" &&
         group_has_installed_skill "$alternate" "$alternate_group"; then
        warn "alternate-root '$alternate_group' skills still depend on templates from '$group': $alternate"
        protected=1
      fi
    done
  done
  if [[ "$protected" -eq 1 ]]; then
    die "Refusing to remove shared templates while dependent skills remain in the alternate discovery root."
  fi
}

preflight_uninstall_same_root() {
  local requested="$1" selected group dependent protected=0
  selected="$(selected_uninstall_groups "$requested")"
  init_agent_target
  for group in $selected; do
    for dependent in $(all_groups); do
      case " $selected " in
        *" $dependent "*) continue ;;
      esac
      if group_depends_on "$dependent" "$group" &&
         group_has_installed_artifact "$dependent"; then
        warn "installed '$dependent' skills still depend on '$group' in the selected discovery root: $CODEX_SKILLS_DIR"
        protected=1
      fi
    done
  done
  if [[ "$protected" -eq 1 ]]; then
    die "Refusing to remove a group while installed groups in the selected discovery root still depend on it."
  fi
}

record_state() {
  local action="$1" group="$2" ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)" || return 1
  ensure_owned_safe_directory "$STATE_DIR" "Installer state directory" || return 1
  if [[ -e "$STATE_FILE" || -L "$STATE_FILE" ]]; then
    checked_validator validate_existing_artifact "$STATE_FILE" file "installer state receipt" || return 1
  else
    (umask 077; : > "$STATE_FILE") || return 1
  fi
  printf '{"repo":"codex-dev-skills","version":"%s","action":"%s","group":"%s","target_mode":"%s","installed_at":"%s"}\n' \
    "$VERSION" "$action" "$group" "$CODEX_DEV_SKILLS_TARGET" "$ts" >> "$STATE_FILE" || return 1
}

remove_transient_skill_files() {
  local root="$1"
  find "$root" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
  find "$root" -depth -type d -name '__pycache__' -empty -delete
}

normalize_staged_file_permissions() {
  local src="$1" staged="$2"
  if [[ -x "$src" ]]; then
    chmod 700 "$staged"
  else
    chmod 600 "$staged"
  fi
}

normalize_staged_tree_permissions() {
  local root="$1"
  python3 - "$root" <<'PY'
import os
import stat
import sys

root = sys.argv[1]
for current, dirs, files in os.walk(root, followlinks=False):
    os.chmod(current, 0o700, follow_symlinks=False)
    for name in dirs:
        path = os.path.join(current, name)
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise SystemExit(f"unsafe staged directory entry: {path}")
        os.chmod(path, 0o700, follow_symlinks=False)
    for name in files:
        path = os.path.join(current, name)
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise SystemExit(f"unsafe staged file entry: {path}")
        os.chmod(path, 0o700 if mode & 0o111 else 0o600, follow_symlinks=False)
PY
}

install_skill() {
  local skill="$1" src dst
  src="$ROOT_DIR/skills/$skill"
  dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
  [[ -d "$src" ]] || die "Missing skill source: skills/$skill"
  sync_dir "$src" "$dst" "skill $skill" 0
}

install_template() {
  local rel="$1" target_rel src dst
  target_rel="$(template_target "$rel")"
  src="$ROOT_DIR/$rel"
  dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
  [[ -f "$src" ]] || die "Missing template source: $rel"
  sync_file "$src" "$dst" "template $target_rel" 0
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
    validate_existing_artifact "$dst" file "agent profile $target_rel"
    if [[ -e "$dst" ]] && ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      if [[ "$action" == "install" ]]; then
        die "Refusing to overwrite existing agent profile: $dst"
      fi
      if [[ "$force" -ne 1 ]]; then
        warn "modified agent profile $target_rel; use update --force after reviewing diff"
        diff -u "$src" "$dst" 2>/dev/null | sed -n '1,80p' || true
        return 1
      fi
      safe_backup_path "$CODEX_CUSTOM_AGENTS_DIR" agent-profiles "$target_rel" >/dev/null
    fi
  done
}

record_agent_profile_state() {
  local item target_rel temp digest
  ensure_owned_safe_directory "$STATE_DIR" "Installer state directory" || return 1
  temp="$(umask 077; mktemp "$STATE_DIR/.codex-dev-skills.$(basename "$PROFILE_STATE_FILE").tmp.XXXXXX")" || return 1
  for item in $(group_agent_profiles codex-agent-profiles); do
    target_rel="$(profile_target "$item")"
    digest="$(file_sha256 "$CODEX_CUSTOM_AGENTS_DIR/$target_rel")" || {
      rm -f "$temp" || true
      return 1
    }
    if ! printf '%s\t%s\n' "$target_rel" "$digest" >> "$temp"; then
      rm -f "$temp" || true
      return 1
    fi
  done
  if ! mv "$temp" "$PROFILE_STATE_FILE"; then
    rm -f "$temp" || true
    return 1
  fi
}

report_loop_cli_dependency() {
  if ! python3 -c 'import yaml' >/dev/null 2>&1; then
    warn "Loop Engineering YAML commands require PyYAML in the selected Python environment."
    info "Install explicitly: python3 -m pip install -r $CODEX_SKILLS_DIR/loop-engineering/requirements.txt"
  fi
}

sync_file() {
  local src="$1" dst="$2" label="$3" force="$4" staging staged parent
  if [[ ! -e "$dst" ]]; then
    parent="$(dirname "$dst")"
    ensure_owned_safe_directory "$parent" "$label destination parent" || return 1
    staging="$(mktemp -d "$parent/.codex-dev-skills.$(basename "$dst").tmp.XXXXXX")" || return 1
    staged="$staging/value"
    if ! cp "$src" "$staged"; then
      rm -rf "$staging"
      return 1
    fi
    if ! normalize_staged_file_permissions "$src" "$staged"; then
      rm -rf "$staging"
      return 1
    fi
    if ! mv "$staged" "$dst"; then
      rm -rf "$staging"
      return 1
    fi
    rmdir "$staging"
    ok "new $label"
    return 0
  fi
  if diff -q "$src" "$dst" >/dev/null 2>&1; then
    ok "up-to-date $label"
    return 0
  fi
  if [[ "$force" -eq 1 ]]; then
    die "Internal error: forced file updates must use the managed transaction"
  fi
  warn "modified $label; use update --force to overwrite after reviewing diff"
  diff -u "$src" "$dst" 2>/dev/null | sed -n '1,80p' || true
  return 1
}

sync_dir() {
  local src="$1" dst="$2" label="$3" force="$4" staging staged parent
  if [[ ! -e "$dst" ]]; then
    parent="$(dirname "$dst")"
    ensure_owned_safe_directory "$parent" "$label destination parent" || return 1
    staging="$(mktemp -d "$parent/.codex-dev-skills.$(basename "$dst").tmp.XXXXXX")" || return 1
    staged="$staging/value"
    if ! mkdir -m 700 "$staged"; then
      rm -rf "$staging"
      return 1
    fi
    if ! cp -R "$src"/. "$staged"/; then
      rm -rf "$staging"
      return 1
    fi
    if ! remove_transient_skill_files "$staged" || ! normalize_staged_tree_permissions "$staged"; then
      rm -rf "$staging"
      return 1
    fi
    if ! mv "$staged" "$dst"; then
      rm -rf "$staging"
      return 1
    fi
    rmdir "$staging"
    ok "new $label"
    return 0
  fi
  if diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" >/dev/null 2>&1; then
    ok "up-to-date $label"
    return 0
  fi
  if [[ "$force" -eq 1 ]]; then
    die "Internal error: forced directory updates must use the managed transaction"
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

TX_SRCS=()
TX_DSTS=()
TX_LABELS=()
TX_EXPECTED=()
TX_ROOTS=()
TX_KINDS=()
TX_RELS=()
TX_BACKUPS=()
TX_IDENTITIES=()
TX_REPLACEMENT_IDENTITIES=()
TX_DEST_PARENT_IDENTITIES=()
TX_BACKUP_PARENT_IDENTITIES=()
TX_STAGING=()
TX_STAGED=()
TX_STATUS=()
RX_PATHS=()
RX_LABELS=()
RX_IDENTITIES=()
RX_REPLACEMENT_IDENTITIES=()
RX_PARENT_IDENTITIES=()
RX_STAGING=()
RX_STAGED=()
RX_OLD=()
RX_STATUS=()

transaction_reset() {
  TX_SRCS=()
  TX_DSTS=()
  TX_LABELS=()
  TX_EXPECTED=()
  TX_ROOTS=()
  TX_KINDS=()
  TX_RELS=()
  TX_BACKUPS=()
  TX_IDENTITIES=()
  TX_REPLACEMENT_IDENTITIES=()
  TX_DEST_PARENT_IDENTITIES=()
  TX_BACKUP_PARENT_IDENTITIES=()
  TX_STAGING=()
  TX_STAGED=()
  TX_STATUS=()
  RX_PATHS=()
  RX_LABELS=()
  RX_IDENTITIES=()
  RX_REPLACEMENT_IDENTITIES=()
  RX_PARENT_IDENTITIES=()
  RX_STAGING=()
  RX_STAGED=()
  RX_OLD=()
  RX_STATUS=()
}

artifact_identity() {
  local path="$1" expected="$2"
  python3 - "$path" "$expected" <<'PY'
import hashlib
import os
import stat
import sys

path, expected = sys.argv[1:]
if not os.path.lexists(path):
    print("missing")
    raise SystemExit(0)

digest = hashlib.sha256()
entries = [(".", path)]
if expected == "directory":
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs.sort()
        files.sort()
        for name in dirs + files:
            child = os.path.join(root, name)
            entries.append((os.path.relpath(child, path), child))
for relative, candidate in entries:
    st = os.lstat(candidate)
    digest.update(relative.encode("utf-8", "surrogateescape") + b"\0")
    digest.update(f"{st.st_dev}:{st.st_ino}:{st.st_mode}:{st.st_uid}:{st.st_size}:{st.st_mtime_ns}".encode())
    digest.update(b"\0")
    if stat.S_ISREG(st.st_mode):
        with open(candidate, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
print(digest.hexdigest())
PY
}

path_identity() {
  python3 -c 'import os, stat, sys; s=os.lstat(sys.argv[1]); print(f"{s.st_dev}:{s.st_ino}:{stat.S_IFMT(s.st_mode)}:{stat.S_IMODE(s.st_mode)}:{s.st_uid}")' "$1"
}

restore_transaction_signal_handlers() {
  trap 'handle_transaction_signal 130' INT
  trap 'handle_transaction_signal 129' HUP
  trap 'handle_transaction_signal 143' TERM
}

begin_recovery_critical_section() {
  trap '' INT HUP TERM
}

end_recovery_critical_section() {
  if [[ "$TRANSACTION_LOCK_HELD" -eq 1 ]]; then
    restore_transaction_signal_handlers
  else
    trap - INT HUP TERM
  fi
}

recover_receipt_failure() {
  local last="$1"
  begin_recovery_critical_section
  rollback_force_update_receipts "$last" || true
  cleanup_receipt_staging || true
  end_recovery_critical_section
}

recover_artifact_failure() {
  local last="$1"
  begin_recovery_critical_section
  rollback_force_update_transaction "$last" || true
  cleanup_transaction_staging || true
  end_recovery_critical_section
}

tx_forward_rename() {
  local index="$1" src="$2" dst="$3" success_status="$4" failure_status="$5"
  trap '' INT HUP TERM
  if mv "$src" "$dst"; then
    TX_STATUS[$index]="$success_status"
    restore_transaction_signal_handlers
    return 0
  fi
  TX_STATUS[$index]="$failure_status"
  restore_transaction_signal_handlers
  return 1
}

rx_forward_rename() {
  local index="$1" src="$2" dst="$3" success_status="$4" failure_status="$5"
  trap '' INT HUP TERM
  if mv "$src" "$dst"; then
    RX_STATUS[$index]="$success_status"
    restore_transaction_signal_handlers
    return 0
  fi
  RX_STATUS[$index]="$failure_status"
  restore_transaction_signal_handlers
  return 1
}

transaction_has_destination() {
  local candidate="$1" existing
  [[ "${#TX_DSTS[@]}" -gt 0 ]] || return 1
  for existing in "${TX_DSTS[@]}"; do
    [[ "$existing" != "$candidate" ]] || return 0
  done
  return 1
}

transaction_add_artifact() {
  local src="$1" dst="$2" label="$3" expected="$4" target_root="$5" kind="$6" rel="$7"
  local backup="" identity index
  checked_validator validate_source_artifact "$src" "$expected" "$label" || return 1
  checked_validator validate_existing_artifact "$dst" "$expected" "$label" || return 1
  identity="$(artifact_identity "$dst" "$expected")" || return 1
  if [[ -e "$dst" ]]; then
    case "$expected" in
      directory)
        diff -rq -x '__pycache__' -x '*.pyc' -x '.DS_Store' "$src" "$dst" >/dev/null 2>&1 && return 0
        ;;
      file) diff -q "$src" "$dst" >/dev/null 2>&1 && return 0 ;;
    esac
    backup="$(safe_backup_path "$target_root" "$kind" "$rel")" || return 1
  fi
  transaction_has_destination "$dst" && return 0
  index="${#TX_SRCS[@]}"
  TX_SRCS[$index]="$src"
  TX_DSTS[$index]="$dst"
  TX_LABELS[$index]="$label"
  TX_EXPECTED[$index]="$expected"
  TX_ROOTS[$index]="$target_root"
  TX_KINDS[$index]="$kind"
  TX_RELS[$index]="$rel"
  TX_BACKUPS[$index]="$backup"
  TX_IDENTITIES[$index]="$identity"
  TX_REPLACEMENT_IDENTITIES[$index]=""
  TX_DEST_PARENT_IDENTITIES[$index]=""
  TX_BACKUP_PARENT_IDENTITIES[$index]=""
  TX_STAGING[$index]=""
  TX_STAGED[$index]=""
  TX_STATUS[$index]="pending"
}

build_force_update_transaction() {
  local requested="$1" group skill rel target_rel item src dst
  transaction_reset || return 1
  for group in $(expand_groups "$requested"); do
    for skill in $(group_skills "$group"); do
      src="$ROOT_DIR/skills/$skill"
      dst="$(safe_path_under_root "$CODEX_SKILLS_DIR" "$skill")" || return 1
      transaction_add_artifact "$src" "$dst" "skill $skill" directory \
        "$CODEX_SKILLS_DIR" skills "$skill" || return 1
    done
    for rel in $(group_templates "$group"); do
      target_rel="$(template_target "$rel")"
      src="$ROOT_DIR/$rel"
      dst="$(safe_path_under_root "$CODEX_TEMPLATES_DIR" "$target_rel")" || return 1
      transaction_add_artifact "$src" "$dst" "template $target_rel" file \
        "$CODEX_TEMPLATES_DIR" templates "$target_rel" || return 1
    done
    for item in $(group_agent_profiles "$group"); do
      target_rel="$(profile_target "$item")"
      src="$ROOT_DIR/$item"
      dst="$(safe_path_under_root "$CODEX_CUSTOM_AGENTS_DIR" "$target_rel")" || return 1
      transaction_add_artifact "$src" "$dst" "agent profile $target_rel" file \
        "$CODEX_CUSTOM_AGENTS_DIR" agent-profiles "$target_rel" || return 1
    done
  done
}

cleanup_transaction_staging() {
  local index staging cleanup_failed=0
  for ((index=0; index<${#TX_STAGING[@]}; index++)); do
    staging="${TX_STAGING[$index]}"
    [[ -n "$staging" && -d "$staging" ]] || continue
    if ! rm -rf "$staging"; then
      warn "Failed to clean transaction staging directory: $staging"
      cleanup_failed=1
    fi
  done
  return "$cleanup_failed"
}

cleanup_receipt_staging() {
  local index staging cleanup_failed=0
  for ((index=0; index<${#RX_STAGING[@]}; index++)); do
    staging="${RX_STAGING[$index]}"
    [[ -n "$staging" && -d "$staging" ]] || continue
    if [[ "${RX_STATUS[$index]}" == "recovery-failed" ]]; then
      warn "Preserving receipt recovery directory for manual recovery: $staging"
      continue
    fi
    if ! rm -rf "$staging"; then
      warn "Failed to clean receipt staging directory: $staging"
      cleanup_failed=1
    fi
  done
  return "$cleanup_failed"
}

intended_profile_path() {
  local target_rel="$1" destination index
  destination="$CODEX_CUSTOM_AGENTS_DIR/$target_rel"
  for ((index=0; index<${#TX_DSTS[@]}; index++)); do
    if [[ "${TX_DSTS[$index]}" == "$destination" ]]; then
      printf '%s\n' "${TX_STAGED[$index]}"
      return 0
    fi
  done
  [[ -f "$destination" && ! -L "$destination" ]] || return 1
  printf '%s\n' "$destination"
}

stage_receipt_file() {
  local path="$1" label="$2" mode="$3" expanded="$4"
  local index parent staging staged old group item target_rel intended digest ts
  parent="$(dirname "$path")"
  ensure_owned_safe_directory "$parent" "$label parent" || return 1
  if [[ -e "$path" || -L "$path" ]]; then
    checked_validator validate_existing_artifact "$path" file "$label" || return 1
    checked_validator validate_receipt_writable "$path" "$label" || return 1
  fi
  index="${#RX_PATHS[@]}"
  staging="$(mktemp -d "$parent/.codex-dev-skills.$(basename "$path").receipt.XXXXXX")" || return 1
  staged="$staging/value"
  old="$staging/original"
  RX_PATHS[$index]="$path"
  RX_LABELS[$index]="$label"
  RX_STAGING[$index]="$staging"
  RX_STAGED[$index]="$staged"
  RX_OLD[$index]="$old"
  RX_STATUS[$index]="pending"
  RX_IDENTITIES[$index]="$(artifact_identity "$path" file)" || return 1
  RX_REPLACEMENT_IDENTITIES[$index]=""
  RX_PARENT_IDENTITIES[$index]="$(path_identity "$parent")" || return 1
  case "$mode" in
    installed-state)
      if [[ -e "$path" ]]; then
        cp "$path" "$staged" || return 1
      else
        (umask 077; : > "$staged") || return 1
      fi
      ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)" || return 1
      for group in $expanded; do
        printf '{"repo":"codex-dev-skills","version":"%s","action":"update","group":"%s","target_mode":"%s","installed_at":"%s"}\n' \
          "$VERSION" "$group" "$CODEX_DEV_SKILLS_TARGET" "$ts" >> "$staged" || return 1
      done
      ;;
    profile-state)
      (umask 077; : > "$staged") || return 1
      for item in $(group_agent_profiles codex-agent-profiles); do
        target_rel="$(profile_target "$item")"
        intended="$(intended_profile_path "$target_rel")" || return 1
        digest="$(file_sha256 "$intended")" || return 1
        printf '%s\t%s\n' "$target_rel" "$digest" >> "$staged" || return 1
      done
      ;;
    *) die "Internal error: unsupported receipt staging mode: $mode" ;;
  esac
  chmod 600 "$staged" || return 1
  checked_validator validate_source_artifact "$staged" file "$label staged receipt" || return 1
  RX_REPLACEMENT_IDENTITIES[$index]="$(artifact_identity "$staged" file)" || return 1
}

stage_force_update_receipts() {
  local expanded="$1" group has_profiles=0
  stage_receipt_file "$STATE_FILE" "installer state receipt" installed-state "$expanded" || {
    cleanup_receipt_staging || true
    return 1
  }
  for group in $expanded; do
    [[ "$group" != "codex-agent-profiles" ]] || has_profiles=1
  done
  if [[ "$has_profiles" -eq 1 ]]; then
    stage_receipt_file "$PROFILE_STATE_FILE" "agent profile state receipt" profile-state "$expanded" || {
      cleanup_receipt_staging || true
      return 1
    }
  fi
}

rollback_force_update_receipts() {
  local last="$1" index status path old staged label current_identity rollback_failed=0
  for ((index=last; index>=0; index--)); do
    status="${RX_STATUS[$index]}"
    path="${RX_PATHS[$index]}"
    old="${RX_OLD[$index]}"
    staged="${RX_STAGED[$index]}"
    label="${RX_LABELS[$index]}"
    case "$status" in
      replaced)
        current_identity="$(artifact_identity "$path" file)" || current_identity="unreadable"
        if [[ "$current_identity" != "${RX_REPLACEMENT_IDENTITIES[$index]}" ]]; then
          warn "CRITICAL: refusing to move identity-drifted $label during rollback; original remains at $old"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        elif ! mv "$path" "$staged.failed"; then
          warn "CRITICAL: failed to move replacement aside while rolling back $label; original remains at $old"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        elif ! mv "$old" "$path"; then
          warn "CRITICAL: failed to restore $label; original remains at $old"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        else
          RX_STATUS[$index]="rolled-back"
        fi
        ;;
      backed-up)
        if [[ -e "$path" || -L "$path" ]] || ! mv "$old" "$path"; then
          warn "CRITICAL: failed to restore $label; original remains at $old"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        else
          RX_STATUS[$index]="rolled-back"
        fi
        ;;
      created)
        current_identity="$(artifact_identity "$path" file)" || current_identity="unreadable"
        if [[ "$current_identity" != "${RX_REPLACEMENT_IDENTITIES[$index]}" ]]; then
          warn "CRITICAL: refusing to move identity-drifted new $label during rollback: $path"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        elif ! mv "$path" "$staged.failed"; then
          warn "CRITICAL: failed to remove newly created $label during rollback: $path"
          RX_STATUS[$index]="recovery-failed"
          rollback_failed=1
        else
          RX_STATUS[$index]="rolled-back"
        fi
        ;;
    esac
  done
  return "$rollback_failed"
}

apply_force_update_receipts() {
  local index path label parent current_identity parent_identity staged old replacement_status failure_status
  for ((index=0; index<${#RX_PATHS[@]}; index++)); do
    path="${RX_PATHS[$index]}"
    label="${RX_LABELS[$index]}"
    parent="$(dirname "$path")"
    staged="${RX_STAGED[$index]}"
    old="${RX_OLD[$index]}"
    parent_identity="$(path_identity "$parent")" || {
      warn "$label parent became unavailable before apply: $parent"
      recover_receipt_failure "$((index - 1))"
      return 1
    }
    current_identity="$(artifact_identity "$path" file)" || {
      warn "$label identity became unreadable before apply: $path"
      recover_receipt_failure "$((index - 1))"
      return 1
    }
    if [[ "$parent_identity" != "${RX_PARENT_IDENTITIES[$index]}" ||
          "$current_identity" != "${RX_IDENTITIES[$index]}" ]]; then
      warn "$label identity changed before apply: $path"
      recover_receipt_failure "$((index - 1))"
      return 1
    fi
    checked_validator validate_source_artifact "$staged" file "$label staged receipt" || {
      recover_receipt_failure "$((index - 1))"
      return 1
    }
    if [[ -e "$path" ]]; then
      if ! rx_forward_rename "$index" "$path" "$old" backed-up pending; then
        warn "failed to stage current $label for replacement: $path"
        recover_receipt_failure "$((index - 1))"
        return 1
      fi
    fi
    if [[ -e "$path" || -L "$path" ]]; then
      warn "CRITICAL: $label path reappeared during replacement; original remains at $old"
      RX_STATUS[$index]="recovery-failed"
      recover_receipt_failure "$((index - 1))"
      return 1
    fi
    if [[ -e "$old" ]]; then
      replacement_status="replaced"
      failure_status="backed-up"
    else
      replacement_status="created"
      failure_status="pending"
    fi
    if ! rx_forward_rename "$index" "$staged" "$path" "$replacement_status" "$failure_status"; then
      warn "failed to replace $label: $path"
      recover_receipt_failure "$index"
      return 1
    fi
  done
}

stage_force_update_transaction() {
  local index src dst label expected target_root backup destination_parent backup_parent staging staged
  local destination_device backup_device
  for ((index=0; index<${#TX_SRCS[@]}; index++)); do
    src="${TX_SRCS[$index]}"
    dst="${TX_DSTS[$index]}"
    label="${TX_LABELS[$index]}"
    expected="${TX_EXPECTED[$index]}"
    target_root="${TX_ROOTS[$index]}"
    backup="${TX_BACKUPS[$index]}"
    destination_parent="$(dirname "$dst")"
    ensure_owned_safe_directory "$target_root" "$label target root" || {
      cleanup_transaction_staging || true
      return 1
    }
    ensure_owned_safe_directory "$destination_parent" "$label destination parent" || {
      cleanup_transaction_staging || true
      return 1
    }
    if [[ -n "$backup" ]]; then
      backup_parent="$(dirname "$backup")"
      ensure_owned_safe_directory "$backup_parent" "$label backup parent" || {
        cleanup_transaction_staging || true
        return 1
      }
      [[ ! -e "$backup" && ! -L "$backup" ]] || {
        warn "Refusing to overwrite existing managed backup path: $backup"
        cleanup_transaction_staging || true
        return 1
      }
      destination_device="$(path_device "$destination_parent")" || {
        cleanup_transaction_staging || true
        return 1
      }
      backup_device="$(path_device "$backup_parent")" || {
        cleanup_transaction_staging || true
        return 1
      }
      if [[ "$destination_device" != "$backup_device" ]]; then
        warn "Refusing cross-filesystem backup rename for $label: $dst -> $backup"
        cleanup_transaction_staging || true
        return 1
      fi
      TX_BACKUP_PARENT_IDENTITIES[$index]="$(path_identity "$backup_parent")" || {
        cleanup_transaction_staging || true
        return 1
      }
    fi
    TX_DEST_PARENT_IDENTITIES[$index]="$(path_identity "$destination_parent")" || {
      cleanup_transaction_staging || true
      return 1
    }
    staging="$(mktemp -d "$destination_parent/.codex-dev-skills.$(basename "$dst").tmp.XXXXXX")" || {
      cleanup_transaction_staging || true
      return 1
    }
    staged="$staging/value"
    TX_STAGING[$index]="$staging"
    TX_STAGED[$index]="$staged"
    if [[ "$expected" == "directory" ]]; then
      mkdir "$staged" || {
        cleanup_transaction_staging || true
        return 1
      }
      if ! cp -R "$src"/. "$staged"/; then
        warn "failed to stage $label"
        cleanup_transaction_staging || true
        return 1
      fi
      remove_transient_skill_files "$staged" || {
        warn "failed to sanitize staged $label"
        cleanup_transaction_staging || true
        return 1
      }
      normalize_staged_tree_permissions "$staged" || {
        warn "failed to secure staged $label permissions"
        cleanup_transaction_staging || true
        return 1
      }
    elif ! cp "$src" "$staged"; then
      warn "failed to stage $label"
      cleanup_transaction_staging || true
      return 1
    elif ! normalize_staged_file_permissions "$src" "$staged"; then
      warn "failed to secure staged $label permissions"
      cleanup_transaction_staging || true
      return 1
    fi
    TX_REPLACEMENT_IDENTITIES[$index]="$(artifact_identity "$staged" "$expected")" || {
      cleanup_transaction_staging || true
      return 1
    }
  done
}

rollback_force_update_transaction() {
  local last="$1" index status dst backup staged label expected current_identity rollback_failed=0 displaced
  for ((index=last; index>=0; index--)); do
    status="${TX_STATUS[$index]}"
    dst="${TX_DSTS[$index]}"
    backup="${TX_BACKUPS[$index]}"
    staged="${TX_STAGED[$index]}"
    label="${TX_LABELS[$index]}"
    expected="${TX_EXPECTED[$index]}"
    case "$status" in
      replaced)
        displaced="$staged.rollback"
        current_identity="$(artifact_identity "$dst" "$expected")" || current_identity="unreadable"
        if [[ "$current_identity" != "${TX_REPLACEMENT_IDENTITIES[$index]}" ]]; then
          warn "CRITICAL: refusing to move identity-drifted $label during rollback; original remains at $backup"
          rollback_failed=1
        elif ! mv "$dst" "$displaced"; then
          warn "CRITICAL: failed to move replacement aside while rolling back $label; original remains at $backup"
          rollback_failed=1
        elif ! mv "$backup" "$dst"; then
          warn "CRITICAL: failed to restore $label; original remains at $backup"
          rollback_failed=1
        else
          TX_STATUS[$index]="rolled-back"
        fi
        ;;
      backed-up)
        if [[ -e "$dst" || -L "$dst" ]]; then
          warn "CRITICAL: refusing to restore $label onto a reappeared destination; original remains at $backup"
          rollback_failed=1
        elif ! mv "$backup" "$dst"; then
          warn "CRITICAL: failed to restore $label; original remains at $backup"
          rollback_failed=1
        else
          TX_STATUS[$index]="rolled-back"
        fi
        ;;
      created)
        current_identity="$(artifact_identity "$dst" "$expected")" || current_identity="unreadable"
        if [[ "$current_identity" != "${TX_REPLACEMENT_IDENTITIES[$index]}" ]]; then
          warn "CRITICAL: refusing to move identity-drifted new $label during rollback: $dst"
          rollback_failed=1
        elif ! mv "$dst" "$staged.rollback"; then
          warn "CRITICAL: failed to remove newly created $label during rollback: $dst"
          rollback_failed=1
        else
          TX_STATUS[$index]="rolled-back"
        fi
        ;;
    esac
  done
  return "$rollback_failed"
}

apply_force_update_transaction() {
  local index dst backup staged label expected current_identity destination_parent backup_parent
  local current_destination_parent_identity current_backup_parent_identity replacement_status failure_status
  for ((index=0; index<${#TX_SRCS[@]}; index++)); do
    dst="${TX_DSTS[$index]}"
    backup="${TX_BACKUPS[$index]}"
    staged="${TX_STAGED[$index]}"
    label="${TX_LABELS[$index]}"
    expected="${TX_EXPECTED[$index]}"
    destination_parent="$(dirname "$dst")"
    current_destination_parent_identity="$(path_identity "$destination_parent")" || {
      warn "Destination parent became unavailable before applying $label: $destination_parent"
      recover_artifact_failure "$((index - 1))"
      return 1
    }
    if [[ "$current_destination_parent_identity" != "${TX_DEST_PARENT_IDENTITIES[$index]}" ]]; then
      warn "Destination parent identity changed before applying $label: $destination_parent"
      recover_artifact_failure "$((index - 1))"
      return 1
    fi
    current_identity="$(artifact_identity "$dst" "$expected")" || {
      warn "Destination identity became unreadable before applying $label: $dst"
      recover_artifact_failure "$((index - 1))"
      return 1
    }
    if [[ "$current_identity" != "${TX_IDENTITIES[$index]}" ]]; then
      warn "Destination identity changed before applying $label: $dst"
      recover_artifact_failure "$((index - 1))"
      return 1
    fi
    if ! checked_validator validate_source_artifact "$staged" "$expected" "staged $label"; then
      warn "Staged artifact became unsafe before applying $label: $staged"
      recover_artifact_failure "$((index - 1))"
      return 1
    fi
    if [[ -n "$backup" ]]; then
      backup_parent="$(dirname "$backup")"
      current_backup_parent_identity="$(path_identity "$backup_parent")" || {
        warn "Managed backup parent became unavailable before applying $label: $backup_parent"
        recover_artifact_failure "$((index - 1))"
        return 1
      }
      if [[ "$current_backup_parent_identity" != "${TX_BACKUP_PARENT_IDENTITIES[$index]}" ]]; then
        warn "Managed backup parent identity changed before applying $label: $backup_parent"
        recover_artifact_failure "$((index - 1))"
        return 1
      fi
      if [[ -e "$backup" || -L "$backup" ]]; then
        warn "Refusing to overwrite managed backup path created after preflight: $backup"
        recover_artifact_failure "$((index - 1))"
        return 1
      fi
      if ! tx_forward_rename "$index" "$dst" "$backup" backed-up pending; then
        warn "failed to create backup for $label at managed path: $backup"
        recover_artifact_failure "$((index - 1))"
        return 1
      fi
    fi
    if [[ -e "$dst" || -L "$dst" ]]; then
      if [[ -n "$backup" ]]; then
        TX_STATUS[$index]="recovery-failed"
        warn "CRITICAL: destination reappeared after backing up $label; original remains at $backup"
      else
        warn "Destination appeared after preflight for $label: $dst"
      fi
      recover_artifact_failure "$((index - 1))"
      return 1
    fi
    if [[ -n "$backup" ]]; then
      replacement_status="replaced"
      failure_status="backed-up"
    else
      replacement_status="created"
      failure_status="pending"
    fi
    if ! tx_forward_rename "$index" "$staged" "$dst" "$replacement_status" "$failure_status"; then
      warn "failed to replace $label; rolling back the complete update"
      recover_artifact_failure "$index"
      return 1
    fi
  done
  return 0
}

report_force_update_transaction() {
  local index backup label
  for ((index=0; index<${#TX_SRCS[@]}; index++)); do
    backup="${TX_BACKUPS[$index]}"
    label="${TX_LABELS[$index]}"
    if [[ -n "$backup" ]]; then
      ok "updated $label (managed backup: $backup)"
    else
      ok "new $label"
    fi
  done
}

force_update_transaction() {
  local requested="$1" expanded group
  expanded="$(expand_groups "$requested")"
  build_force_update_transaction "$requested" || return 1
  if [[ "${#TX_SRCS[@]}" -gt 0 ]]; then
    stage_force_update_transaction || return 1
  fi
  stage_force_update_receipts "$expanded" || {
    cleanup_transaction_staging || true
    return 1
  }
  TRANSACTION_APPLY_ACTIVE=1
  if [[ "${#TX_SRCS[@]}" -gt 0 ]] && ! apply_force_update_transaction; then
    TRANSACTION_APPLY_ACTIVE=0
    cleanup_receipt_staging || true
    return 1
  fi
  if ! apply_force_update_receipts; then
    begin_recovery_critical_section
    if [[ "${#TX_SRCS[@]}" -gt 0 ]]; then
      rollback_force_update_transaction "$(( ${#TX_SRCS[@]} - 1 ))" || true
    fi
    TRANSACTION_APPLY_ACTIVE=0
    cleanup_transaction_staging || true
    cleanup_receipt_staging || true
    end_recovery_critical_section
    return 1
  fi
  TRANSACTION_APPLY_ACTIVE=0
  cleanup_transaction_staging || warn "Update committed, but transaction staging cleanup is incomplete."
  cleanup_receipt_staging || warn "Update committed, but receipt staging cleanup is incomplete."
  report_force_update_transaction
  for group in $expanded; do
    info "Updating $group"
    [[ "$group" != "codex-delivery-workflow" ]] || report_loop_cli_dependency
  done
}

install_group() {
  local group="$1" item
  info "Installing $group"
  ensure_owned_safe_directory "$CODEX_SKILLS_DIR" "CODEX_SKILLS_DIR target root" || return 1
  ensure_owned_safe_directory "$CODEX_TEMPLATES_DIR" "CODEX_TEMPLATES_DIR target root" || return 1
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
  ensure_owned_safe_directory "$CODEX_SKILLS_DIR" "CODEX_SKILLS_DIR target root" || return 1
  ensure_owned_safe_directory "$CODEX_TEMPLATES_DIR" "CODEX_TEMPLATES_DIR target root" || return 1
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
  printf 'Codex skills target mode: %s\n' "$CODEX_DEV_SKILLS_TARGET"
  printf 'Codex skills target: %s\n' "$CODEX_SKILLS_DIR"
  if alternate_standard_skills_root >/dev/null; then
    printf 'Alternate discovery target: %s\n' "$(alternate_standard_skills_root)"
  fi
  printf 'Codex templates target: %s\n' "$CODEX_TEMPLATES_DIR"
  printf 'Custom agents target: %s\n' "$CODEX_CUSTOM_AGENTS_DIR"
  printf 'State file: %s\n\n' "$STATE_FILE"
  report_cross_root_skill_collisions
  printf '\n'
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
    preflight_uninstall_cross_root "$requested"
    init_targets
    preflight_uninstall_same_root "$requested"
    for group in $(selected_uninstall_groups "$requested"); do
      uninstall_group "$group"
    done
  fi
}

main() {
  local cmd="${1:-}" requested="" force=0 group transaction_status=0
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

  case "$cmd" in
    install)
      preflight_plugin_distribution_collision
      preflight_targets
      preflight_cross_root_skill_collisions "$requested"
      preflight_filesystem_sync install "$requested" 0
      for group in $(expand_groups "$requested"); do
        if [[ "$group" == "codex-agent-profiles" ]]; then
          preflight_agent_target
          preflight_agent_profile_sync install 0
          break
        fi
      done
      preflight_nonforce_state "$requested"
      init_targets
      run_for_groups install "$requested"
      ;;
    update)
      preflight_plugin_distribution_collision
      preflight_targets
      preflight_cross_root_skill_collisions "$requested"
      for group in $(expand_groups "$requested"); do
        if [[ "$group" == "codex-agent-profiles" ]]; then
          preflight_agent_target
          break
        fi
      done
      preflight_filesystem_sync update "$requested" "$force"
      for group in $(expand_groups "$requested"); do
        if [[ "$group" == "codex-agent-profiles" ]]; then
          preflight_agent_profile_sync update "$force"
          break
        fi
      done
      if [[ "$force" -eq 1 ]]; then
        acquire_transaction_lock || return 1
        if ! force_update_transaction "$requested"; then
          transaction_status=1
        fi
        if ! release_transaction_lock; then
          transaction_status=1
        fi
        trap - EXIT INT HUP TERM
        return "$transaction_status"
      else
        preflight_nonforce_state "$requested"
        init_targets
        run_for_groups update "$requested" 0
      fi
      ;;
    diff)
      init_targets
      run_for_groups diff "$requested"
      ;;
    uninstall) cmd_uninstall "$@" ;;
  esac
}

main "$@"
