# Issue #186 Repository Validation Timing Evidence

## Baseline

The Issue #186 description records a pre-sharding local observation of 855
discovered tests taking approximately 1,691 seconds. Two concurrent
`cli-session-handoff` tests failed during that run and passed when rerun
individually. This is issue-reported baseline evidence, not a reproducible SLA
or a hosted-run measurement.

The v0.20.0 implementation baseline currently discovers 879 tests across 62
test modules. That inventory count is structural evidence only and does not
replace the issue's duration observation.

The latest successful pre-change hosted baseline is GitHub Actions run
[`33136972526`](https://github.com/jeffery777/codex-dev-skills/actions/runs/33136972526/job/98739030829),
job `98739030829`, at head `736e5e40bb3d8bb6b5678765739b3b8437bcf920`.
The single `Validate repository` job started at `2026-08-28T02:47:49Z`,
completed successfully at `2026-08-28T03:01:56Z`, and therefore took about
847 seconds. The GitHub connector verified the run, job identity, and success;
the GitHub API was used only to recover timestamps omitted by the connector.
The workflow itself started at `2026-08-28T02:47:31Z`, so the comparable
workflow-start-to-required-check-completion boundary took 865 seconds. This is
the hosted before-measurement for the post-change comparison below.

## Local Shard Observation

On 2026-08-28, the Issue #186 working tree used the pinned Python 3.12.9
interpreter to run every final functional boundary independently. The manifest
contains 63 modules after adding its own contract test.

| Shard | Tests | Test-process wall time (seconds) |
| --- | ---: | ---: |
| `exact-head-merge` | 76 | 1.36 |
| `gitnexus` | 138 | 86.72 |
| `installer-agent-profiles` | 48 | 240.96 |
| `installer-runtime` | 49 | 700.31 |
| `loop-context` | 93 | 0.84 |
| `loop-control` | 83 | 22.84 |
| `memory-m0` | 67 | 4.19 |
| `memory-m1-and-evaluation` | 80 | 12.89 |
| `native-runtime` | 84 | 41.64 |
| `operational-improvement` | 87 | 7.28 |
| `plugin-packaging` | 12 | 15.65 |
| `repository-policy` | 74 | 61.14 |

The observed local test-process critical path is therefore approximately
700.31 seconds. The first coarse `installer-packaging` boundary took 959.65
seconds; splitting it into stable agent-profile, runtime-installer, and plugin
packaging ownership reduced that local test-body critical path without using
test order or arbitrary method buckets. These runs occurred concurrently on
one development host, exclude hosted runner setup and queue time, and are not a
before/after hosted comparison.

## Post-change Hosted Measurement

The first successful Repository Validation run for pull request #194 provides
the post-change hosted observation:

| Field | Value |
| --- | --- |
| Repository / pull request | `jeffery777/codex-dev-skills` / `#194` |
| Exact head SHA | `51092d08b2d448fadd7a6844eb24f9cbb09c10aa` |
| Workflow run ID and URL | [`33143132719`](https://github.com/jeffery777/codex-dev-skills/actions/runs/33143132719) |
| Runner label | `ubuntu-latest` |
| Observed runner image | `ubuntu-24.04` (`ubuntu24/20260823.283`) |
| Python version | `3.12.9` |
| Structural-check duration | 40-second job; 8-second repository-check step |
| Aggregate result | `Validate repository` job `98759552109`: success |
| Hosted critical-path duration | 520 seconds from run start to aggregate completion |

| Shard | Hosted job duration (seconds) | Test-step duration (seconds) |
| --- | ---: | ---: |
| `exact-head-merge` | 25 | 1 |
| `gitnexus` | 41 | 17 |
| `installer-agent-profiles` | 130 | 108 |
| `installer-runtime` | 492 | 468 |
| `loop-context` | 27 | 1 |
| `loop-control` | 28 | 5 |
| `memory-m0` | 30 | 6 |
| `memory-m1-and-evaluation` | 44 | 21 |
| `native-runtime` | 36 | 11 |
| `operational-improvement` | 59 | 9 |
| `plugin-packaging` | 32 | 9 |
| `repository-policy` | 73 | 45 |

The workflow started at `2026-08-28T04:53:44Z`; the aggregate completed at
`2026-08-28T05:02:24Z`. Compared on the same workflow-start-to-required-check
boundary with the 865-second pre-change run, this observation is 345 seconds
shorter, or approximately 39.9%. The `installer-runtime` test step is the
hosted critical path at 468 seconds; its
492-second job duration includes 24 seconds of setup and teardown. The full
workflow adds planning, scheduling, and aggregate overhead beyond that job.

This is one observed before/after comparison, not an SLA. Module count alone
does not predict duration, runner conditions vary, and future performance is
not guaranteed by this single successful run.
