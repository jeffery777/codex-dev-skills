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
This is the hosted before-measurement for the post-change comparison below.

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

To be completed from the first successful exact-head Repository Validation run
for the Issue #186 pull request:

| Field | Value |
| --- | --- |
| Repository / pull request | Pending |
| Exact head SHA | Pending |
| Workflow run ID and URL | Pending |
| Runner image | Pending |
| Python version | Pending |
| Structural-check duration | Pending |
| Per-shard durations | Pending |
| Aggregate result | Pending |
| Hosted critical-path duration | Pending |

The final comparison must report observed wall-clock and critical-path effects,
including setup overhead. It must not claim that module count alone predicts
duration or that a single hosted observation guarantees future performance.
