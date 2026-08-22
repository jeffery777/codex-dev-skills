# Issue #165 Empirical Paired-Run Evidence

Date: 2026-08-22

This artifact records one bounded same-objective comparison between a
compressed-current-context proxy and a fresh durable-checkpoint proxy. It
satisfies the Issue #165 empirical evidence gate for this release candidate;
it is not a general claim that fresh rollover is always cheaper or better.

## Provenance And Method

- Repository: `jeffery777/codex-dev-skills`
- Base: `944a65a71b0d15b757627a91f1fb97279e3dc8ac`
- Head under test: `4d66efa0429d55b7c4ab8e6399387244684e8960`
- Objective ID: `issue-165-release-readiness-v2`
- Runtime: `codex-cli 0.149.0`
- Explicit model: `gpt-5.6-terra`
- Execution: sequential, read-only, ephemeral `codex exec --json` runs in the
  same worktree; compressed-current-context ran first.
- Shared objective: audit the exact base/head context-continuity contract and
  identify the current release blocker from repository and Git evidence.
- Only the context preamble differed. The compressed condition supplied an
  advisory summary of the ongoing implementation/review history. The fresh
  condition supplied only repository, branch, base, head, objective, authority,
  and writer-boundary checkpoint fields.
- Token totals are CLI-reported `input_tokens + output_tokens`. Because the
  complete prompt is input to each invocation, the fresh total includes its
  checkpoint/bootstrap prompt. No tokenizer estimate was substituted.
- Declared reads are the unique repository paths in each schema-valid final
  result. Completed command counts and exact repeated commands come from
  completed command events in the raw JSONL.
- Review/fix rounds are zero because the paired objective is a read-only audit.

The complete JSONL is intentionally not committed because command events carry
machine-local absolute paths and runtime log material that repository policy
forbids syncing. Exact prompt and JSONL SHA-256 digests bind the retained local
scan artifacts. The durable, release-safe
[`paired-run-results.json`](paired-run-results.json) preserves both complete
schema-valid final results, usage, event-count inputs, rubric disposition, and
source hashes without those excluded local fields. The principal measurements
are also reproduced below.

## Predeclared Quality Rubric

One point was assigned for each item, with no partial credit:

1. exact objective ID, base, and head;
2. `ASSESSMENT_ONLY`, `TWO_ROUNDS`, and `NO_AUTOMATIC_ROLLOVER` with a
   repository-grounded explanation;
3. `PARALLEL_DELEGATION`, `FORK_WITH_HISTORY`, and
   `FRESH_FROM_CHECKPOINT` with their distinct semantics;
4. `DURABLE_CHECKPOINT`, `SINGLE_WRITER`, `SOURCE_STOP_WRITING`, `LINEAGE`,
   `IDEMPOTENCY`, and `ANTI_RECURSION`;
5. `DESKTOP`, `CLI`, `IDE`, `SAFE_FALLBACK`, and
   `NO_UNPUBLISHED_INTERNALS`;
6. `ADVISORY_ONLY`, `NO_TASK_AUTHORITY`, `NO_OWNERSHIP_AUTHORITY`, and
   `NO_COMPLETION_AUTHORITY` for graph lineage;
7. `release_evidence_flag=false` for the committed synthetic suite;
8. an empirical paired-run blocker without a false push, PR, merge, tag, or
   release-completion claim.

Both final results scored 8/8. The first aggregate scorer returned 7/8 for both
because check 8 required the English word `empirical` while both schema-valid
answers described that blocker in Traditional Chinese. Raw outputs were not
changed. The disposition corrected only that language-dependent predicate:
each result had a non-empty paired-run evidence blocker,
`release_evidence_flag=false`, and no prohibited completion claim.

## Raw Result Summary

| Metric | Compressed current context | Fresh durable checkpoint |
| --- | ---: | ---: |
| prompt bytes | 2,244 | 2,277 |
| input tokens | 377,419 | 163,433 |
| output tokens | 4,582 | 2,816 |
| objective total tokens including bootstrap | 382,001 | 166,249 |
| cached input tokens, included in input total | 301,312 | 115,712 |
| wall time | 99.846 s | 64.758 s |
| declared unique repository reads | 16 | 10 |
| completed command events | 7 | 4 |
| exact repeated commands | 0 | 0 |
| review/fix rounds | 0 | 0 |
| stale-context errors | 1 | 0 |
| blockers | 1 | 1 |
| final quality | 8/8 | 8/8 |

The shared blocker in both raw results was the pre-run repository state: the
committed synthetic fixture did not itself satisfy the empirical paired-run
gate. The compressed result also rejected the deliberately stale suggested
path `docs/context-continuity-rollover.md` and selected
`docs/context-continuity.md`; the fresh result went directly to the existing
path and reported no stale-context error.

Relative to the compressed condition, the fresh condition used 56.48% fewer
objective tokens, 35.14% less wall time, 37.50% fewer declared repository
reads, and 42.86% fewer completed command events while preserving 8/8 quality.

## Artifact Digests

- compressed prompt:
  `59abd56ccaa283725c05bdd267fed601ee37f145ad5e85245e8bc46fb7da83e0`
- fresh prompt:
  `d832d9829c6c8708d0dd7453c3f7f7832721b150b6b614f60ee128c73aeb618e`
- compressed raw JSONL:
  `80986125ff7eda59235c2efde9a7cab3efcdc2445ea5cd43fd0a02792c48ed62`
- fresh raw JSONL:
  `42dd9b4849539c27d062b1e5711134e4486ff394317754bb9d7c1ecd3dea3215`
- original aggregate summary:
  `6b64729df1ccd667532b2ae8593a54def781d5df97478ebac68ac82342cf11ab`
- rubric:
  `91db7d9146257c305c2ecc7134c53814a2141b53cb988b0d8a219297794c422b`
- language-neutral rescored summary:
  `02611de160f3b0238ec8e3b9d804aadc618132d5f9ae9a0b3ca2a2d39ae9c718`

## Interpretation And Limits

This pair supports fresh rollover for the tested audit objective without a
quality regression. It does not isolate order effects, shared-cache effects,
model variance, other objectives, interactive sessions, or product-surface
latency. The compressed condition ran first, so the comparison must not be
represented as a universal performance benchmark. Runtime task creation,
writer transfer, commit, push, PR, merge, tag, and release remained outside
both runs.
