# P5 Final Codex Security Diff Scan

Gate result: **PASS**.

Codex Security scan `559c572f-d3fe-44a0-a6f3-c13be1e78521` completed and
finalized natively against the immutable branch-diff snapshot
`a75728b15f5d15ba7bf1a7e6e3a2dd934915592e..e91b3cf69b711c9bb5deeb4f87ec43af4a42456e`.
The deterministic reviewed-diff snapshot digest was
`codex-security-snapshot/v1:sha256:2c3c584aeea666cd4f8bb4eff1035e90fe9c2d3173a536492b3a1f9f359e89b4`.

Native result:

- status: `complete`;
- coverage: `complete`, 13/13 diff-worklist rows closed;
- candidate ledgers: 7/7 contain discovery, validation, and attack-path
  dispositions;
- reportable findings: 0;
- deferred rows or open questions: 0;
- external, remote, or production targets accessed: none;
- live Linux execution: not performed; portability remains fixture/contract
  evidence only.

The seven plausible-looking rows were independently validated. Each stopped at
a local diagnostic, synthetic evaluation, or advisory integrity signal and
could not cross into protected-event, mutation, query/context adoption, gate,
merge, publication, or completion authority. The mechanical final policy for
all seven was `ignore`; the canonical `findings.json` is empty. This disposition
does not turn the rejected rows into completion evidence; completion continues
to depend on the repository verification, formal code/docs gates, and
publication readback.

Canonical finalized artifact digests:

- `scan-manifest.json`:
  `2c8a02861287b0c0d2c5cfbbfd29a34baa34d87ca53dab31ffa072a872089651`;
- `report.md`:
  `274f05837ea8a19625070a5afc90564f7e1cfcce4b6ca170362e69e08c54c40d`;
- `coverage.json`:
  `818f7f93f42672b945e4faeab7308f6d00a099fe52291e7b9c172e3ea5b71c87`;
- `findings.json`:
  `a067e0b73a11c321c04cf0e23158c9c00d0f8c97188e9e1691f0e7f0acc1d467`;
- `exports/results.sarif`:
  `63f4141364bad863bb82f3c6120915d5c0e4bffe08c6fe8def49f8ea5a8cdff0`.

The first native completion attempt sealed the artifacts but detected that the
pre-finalization manifest serialization was not canonical. The scan remained
running. Re-serializing the unchanged JSON semantics through the plugin's own
canonical writer made the raw bytes match the required projection; the next
native completion call succeeded. No target-repository content, finding
disposition, scope, or scan contract changed during that recovery.

The completed native scan is the security completion authority. The blocked
Goal and individual worker outcomes are coordination evidence only.

## Complexity And Runtime Routing

| Packet | Ambiguity / depth / context | Risk / write radius / verification | Selected profile | Runtime mapping | CP rationale |
| --- | --- | --- | --- | --- | --- |
| capability preflight | low / shallow / small | read-only / none / low | `loop_v2a_mechanical_reader` | `gpt-5.6-luna`, low | Mechanical config extraction needed the lowest sufficient tier. |
| repository threat model | medium / deep / medium | security and public-contract / scan-artifact-only / high | `loop_v2a_security_reviewer` | `gpt-5.6-sol`, high | Repository-wide trust-boundary reasoning required the security review tier. |
| three disjoint file-review shards | high / deep / high | security and data boundary / read-only target / high | `loop_v2a_security_reviewer` | `gpt-5.6-sol`, high | Thirteen full-file rows were independent but required source/control/sink and counterevidence analysis. |
| three candidate validations and reportability closures | high / deep / medium | security and contract / scan-artifact-only / high | `loop_v2a_security_reviewer` | `gpt-5.6-sol`, high | Each candidate needed bounded reproduction plus independent policy calibration. |
| canonical report assembly | medium / medium / medium | public artifact schema / scan-artifact-only / high | `loop_v2a_balanced_worker` | `gpt-5.6-terra`, medium | Deterministic cross-file assembly needed balanced implementation capacity, not a deep reviewer. |

All packets were independent and ownership-bounded. No packet was routed to the
exceptional tier; its multi-trigger threshold was not met. No selected packet
was cost-degraded. The parent independently reconciled 13 work receipts, 7
candidate-ledger chains, canonical schemas, and all 17 manifest hashes before
native finalization. Scan-worker receipts remain non-authoritative for
completion (`completion_proven: false`).
