# P5 source-rebound authorization and corrective migration

Status: **authorized, bounded, replayed, and independently audited**.

## Authority

The delegating user explicitly authorized the bounded validator-contract
correction and Goal recovery in the controlling Codex task. That authority is
limited here to rebinding the active Issue #97 ledger from its verified
`a75728b15f5d15ba7bf1a7e6e3a2dd934915592e` source checkpoint to the already
published branch checkpoint
`67be3d967e39eeab47394d0856963faff8aa4acb`, dispositioning the expired claims
already represented by the unpublished recovery chain, and rebuilding that
chain under the corrected protected-action contract.

This receipt does not authorize merge, release, deployment, destructive Git
operations, repository reset, or changes to any global profile repository.

## Corrective migration boundary

Round-13 review established that `source_rebound` can disposition fenced
claims and therefore must be a protected action. The previously generated,
uncommitted sequence 31-34 chain predated that correction. Its exact pre-fix
artifact digests were preserved before replacement:

- materialized ledger: `e11efc27cd248b51efee689bf44426696943ea414ef15b36390acaca05611ff7`;
- event 31: `27d9003262e49624859606c73d10e3beb5e5720c36a104b29a919e88d457fb6e`;
- event 32: `65f3c8ee1584be9dccf3fb45843eaf5eab89372b54faff19f3283d405d8b8749`;
- event 33: `8fc4d13b34b9900d347d2f65ab288a434b5d7d9b17be9b66fcbd34b17f45d2e5`;
- event 34: `a56c4163a32da0587dcc5919a75504368219a6a3fcb0d579bf81e2dd76f29d2f`.

The verified sequence-30 protected-history digest is
`9b1c74558d60d4e118a246340dcb3a6e00d23503545bcf318ee2a727d125f2e0`.
The corrective replay must start from the exact HEAD ledger blob, must use the
production `loopctl apply-event` write boundary, and must supply current-session
`source_rebound` authorization plus that independently verified history digest.
Events 32-34 must then be regenerated from their unchanged semantic payloads
and the resulting hash chain. The materialized ledger must pass structural and
semantic audit after replay.

## Replay result

The corrective replay used the production `loopctl apply-event` boundary. The
protected event received exact live `source_rebound` authorization and the
verified sequence-30 protected-history digest. Events 32-34 were then
regenerated from their unchanged semantic payloads and the new chain:

- event 31 artifact digest: `cb2041bd7873ac0300d41bdee7f2f0f19952131ccb3b9e92e492d57216329465`;
- event 32 artifact digest: `e3e7b4b0a5effca522934fcd0bfae08e4210830cf2205c376dcbb386679d434d`;
- event 33 artifact digest: `0d2cf25290716180d0653252379269c0785b767cfc1335da00de3c666632a5df`;
- event 34 artifact digest: `8d4fe0a08bd84785f355b5e4fbee404c69a6cf4ddd75f0ac9b198136aac8b6d8`;
- final event hash: `20e5b241d307640e5027130ced9f837da7bbeaa38521bd25b98464504f921932`;
- final protected-history digest: `586383cfe0f44941c90874105fbd63c82fefd13c7fd7ddf948fa6a984a734c59`.

Both the executable semantic audit and the repository ledger validator passed
with 34 events. The first replay attempt rejected before event application
because the corrective generator had not preserved the tracked ledger mode;
the exact partial state was classified, the generator was corrected, and the
successful replay preserved `0644`. A persistent regression now requires
`loopctl` atomic replacement to retain the original ledger mode.
