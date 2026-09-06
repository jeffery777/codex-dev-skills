# Memory Qualification V0 Portable Reference

Use this reference with `scripts/qualificationctl.py`.

`loop-memory-qualification/v0` composes unchanged V3-B result/verification
pairs into a safety/conformance-only off/on wrapper. Wrapper `memory-on` is not
a V3-B mode and requires a separately caller-accepted future M1 qualification
receipt document. Exact proposal/source/input/policy/comparison/verifier
bindings must match. The M1 receipt must bind the exact qualification id,
adapter fingerprints, common V3-B tuple, safety observation, and execution
receipts; digest membership alone is insufficient.
The on arm must report at least one backend touch and one execution-receipt
digest; zero-touch on evidence fails closed.

Memory-off is complete, default, and has zero backend/filesystem touch. Results
are conformant-awaiting-human-decision, not-conformant, or
memory-on-unavailable. Efficacy and promotion claims remain prohibited.

Resolve `LOOP_SKILL_DIR` to the absolute installed `loop-engineering` directory
containing `SKILL.md`, and `LOOP_PYTHON` to the absolute interpreter already
selected and verified for this environment. The commands below use those
resolved values; they do not assume the target repository contains
`./scripts/project-python` or this source tree. Follow the target repository's
environment rules and do not install into or substitute another interpreter.
Only when maintaining the **codex-dev-skills source checkout**, use its tracked
`./scripts/project-python` instead of `"$LOOP_PYTHON"`; all checks, scripts,
evals, and tests in that checkout must use its pinned resolver.

```bash
"$LOOP_PYTHON" "$LOOP_SKILL_DIR/scripts/qualificationctl.py" --help
"$LOOP_PYTHON" "$LOOP_SKILL_DIR/scripts/qualificationctl.py" evaluate \
  <input.json> <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted.json>
"$LOOP_PYTHON" "$LOOP_SKILL_DIR/scripts/qualificationctl.py" validate-result \
  <result.json> <input.json> <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted.json>
```

The wrapper has no backend, execute, promote, install, or activation route.
