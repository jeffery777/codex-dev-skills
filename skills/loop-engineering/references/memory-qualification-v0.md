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

```bash
./scripts/project-python <installed-loop-engineering>/scripts/qualificationctl.py --help
./scripts/project-python <installed-loop-engineering>/scripts/qualificationctl.py evaluate \
  <input.json> <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted.json>
./scripts/project-python <installed-loop-engineering>/scripts/qualificationctl.py validate-result \
  <result.json> <input.json> <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted.json>
```

The wrapper has no backend, execute, promote, install, or activation route.
