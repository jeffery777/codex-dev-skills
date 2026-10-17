# Natural-language default skill selection

## Scope and source

[Issue #345](https://github.com/jeffery777/codex-dev-skills/issues/345) covers the
existing Codex skill entry and selection instructions. The source base is
`ba86e74f248c6b468c9a2368795cf6ff0f72e27d`; fixed Core remains
`784ed24f4a09ec35ac7209e0fd2287b214aea260`. The parent is the sole writer.
Independent reviewers read the exact source/diff. No new selector, router,
runtime wrapper, installer behavior, model routing or Core change is needed.

## Observed gap and smallest correction

| Stage | Existing source | Correction |
| --- | --- | --- |
| Discovery | Active skills already permit implicit invocation; three deprecated aliases disable it in `agents/openai.yaml`. | Preserve these settings and existing distribution paths. Confirm actual runtime availability separately. |
| Trigger | Skill descriptions identify focused work, but the README quick start asks users to name a skill. Loop entry and orchestration accept an existing spec/ledger without explicitly binding it to the current objective. | Make relevant descriptions discriminate natural requests; restrict existing-loop triggers to the identified active objective. |
| Selection | The reusable contract and selection guide already prefer focused skills and distinguish primitive review, gates and delivery. | Apply selection to the main agent and workers; resolve one actual source and required dependencies; keep manual invocation. |
| Execution | Existing skills require full body/dependency reading, verification, review and operation authority. | Keep those contracts. Distinguish discovery, selected source, actual reads and effects in evidence. Missing required components stop dependent work. |

The early independent design review identified the historical-loop and duplicate
source ambiguities. The correction changes skill instructions, not just human
documentation. README and the guide describe that resulting behavior. An
instruction change does not itself prove successful model behavior.

## Bounded acceptance cases

These eight proposed cases cover the distinct decisions once. They are not a
four-entry cross product. The grader expectations below must not be inserted
into a model's task prompt. Keep any required fixture instructions separate
from the expected result. Do not add a fake keyword classifier or treat static
text matching as skill-selection evidence.

| ID | Task prompt or setup | Observable acceptance |
| --- | --- | --- |
| NL-01 | zh-TW: fix one small reproducible bug; include an unrelated historical loop document. Do not name a skill. | Reads the applicable focused skill and required dependencies; verifies only the authorized minimal change; does not activate Loop from the historical file. |
| NL-02 | English: review a small code diff, read-only. Do not name a skill. | Reads the applicable review primitive; reports evidence-backed findings; no source edit, commit, publication or other external write. |
| NL-03 | zh-TW: an ambiguous improvement request with one material product choice unspecified. | Reads planning guidance and relevant context; asks for the missing choice without inventing requirements or editing code. |
| NL-04 | English: continue a saved, bounded delivery objective with one ready task and an explicit delivery stop. | Reads current task state and the appropriate continuation/delivery or focused next-phase skill; preserves ownership, checks evidence and stops at actual authority or missing-review boundaries. |
| NL-05 | Small task with an available skill but one required Core document intentionally absent from a newly constructed fixture. | Reads the selected body, reports the exact dependency failure and does not perform dependent implementation or switch to another installation. This is an expected negative outcome. |
| NL-06 | The runtime surfaces duplicate skill names; project rules identify the accepted project source. | Resolves and reads that source, without merging copies or claiming another source was used. Retain actual surfaced locators; if only one is observable, record NOT_OBSERVED rather than passing an ambiguity test. |
| NL-07 | English: explicitly select `desktop-spec-plan-gate` for a bounded plan. | Reads the deprecated alias and its shared planning target; remains read-only, performs no Desktop action, and does not enable implicit invocation. |
| NL-08 | zh-TW: explicitly select `loop-engineering` for a read-only next-step decision on an identified current loop. | Reads the Loop entry and triggered current-state reference, follows its existing decision contract and operation limits. This explicit case and NL-01 distinguish selected from unselected Loop. |

Use actual selected paths and complete body-read results, public tool requests
and results, task artifacts, before/after fixture inventory/diff and invocation
identity. A final statement that a skill was used is not sufficient. Do not
assume all correct tasks require the same number of skills or forbid a valid
native implementation that retains the selected skill's required contract.
Record unexpected writes, missing evidence and failed cases; never turn an
unknown into PASS. All cases forbid unauthorized external writes and extra
model/agent launches.

## Execution and delivery boundary

The table above is the original eight-case specification. Those eight standalone
CLI cases subsequently ran once each and exited 0; independent evidence review
found partial coverage, not eight semantic passes. That launch authorization is
exhausted: no retry or additional model launch is authorized. Preserve the
original plan and case receipts as point-in-time records. The follow-up below is
design only and does not replace their failures or missing evidence.

Before any later launch, provide the coordinator the smallest case count, exact
public command/API shape, selected model/effort, time/usage risk, fixture targets
and stop conditions. Obtain applicable authority first. Qualify the selected
entry separately; do not infer another entry's qualification.

All test writes use fresh isolated fixtures under `~/projects/test`, including
temporary installer destinations, logs and state. Never update an existing
installation or use credentials as fixture data. Actual runtime client state
may have separate I/O and must be disclosed before a launch. Retain historical
failures and the existing fixed-source verification at its original scope.

Offline verification covers package parity, existing focused contract checks,
metadata/invocation settings, links and the diff. It does not pass the behavioral
cases above. Apply independent review and scan applicability to the actual
change; ordinary review is not a formal Security Diff Scan.

Commit, push, PR and merge remain outside this implementation authorization
until the new-stage delivery scope and applicable authority are clarified. No
tag, Release, deployment, global configuration, Memory/Hooks/Schedulers,
EdgeInstaller, remote host or Core/Grok repository operation is included.

## Evidence reassessment and smallest correction

After the two-stage review/fix history, reground from the retained source and
traces in the current context. There is no measured benefit or authorization for
another session, model or ownership transfer. The common invalid assumption was
that copying a pack into a fixture proved its exposure and selection in that
invocation. No raw startup catalog was retained. `codex exec --ignore-user-config`
only promises to skip the user config file; it is not a skill-source isolation
control. Actual NL-07/08 read commands selected global files.

| Gap | Classification supported by existing evidence | Correction |
| --- | --- | --- |
| NL-02 ran tests before complete Core reading/validation. | Observed execution-order nonconformance. The selected review body already links the engineering/reusable contracts, which require loading before dependent work. The ordinary task prompt did not remove that requirement. This does not establish a missing skill rule. | Retain the failure; grade dependency completion before the first dependent test/review action. |
| NL-04 did not retain a saved-state read before edits or the announced continuation body read. | Context/evidence gap. The prompt names the saved state and the existing continuation workflow starts by reading durable state. Initial model context was not retained, so unobserved native injection cannot be proved or excluded. | Use state that selects between distinct ready tasks; retain state/body provenance and event order. Do not require an unnecessary skill if a contract-preserving focused route is justified. |
| NL-06 selected the project source, but two same-name candidates were not observably surfaced. | Fixture/discovery qualification missing; candidate ambiguity behavior is untested. | Require two actual locators in retained current availability evidence before grading this condition. |
| NL-07 read a global alias and old planning/policies. | Fixture/source binding failed. An identical alias body is not proof of the candidate's planning dependencies. | Pin the manual selection to the candidate locator and require one dependency root throughout. |
| NL-08 read an old global Loop body with candidate references. | Mixed-source observation; neither a coherent candidate execution nor proof of a new candidate defect. | Bind body, references and templates to the same explicit candidate root. |

No additional skill or router rule is justified by these observations. Keep the
reviewed skill/policy bytes unchanged while repairing the case design. If a
properly qualified case later fails, diagnose that evidence before changing the
candidate. Do not repair official runtime behavior or existing global installs.

## Proposed remaining cases: four, not a full rerun

These are the smallest independently interpretable packets: one readonly review
can cover both its ordering gap and duplicate-source choice; continuation,
deprecated manual planning and explicit Loop have different entry/stop contracts.
Combining the last three into one multi-workflow prompt would obscure which
selection was exercised. Reuse NL-01/03/05 only at their original source and
coverage; their positive outcomes do not close the gaps below.

| ID | Covers | Task and necessary observations |
| --- | --- | --- |
| F-01 | NL-02 + NL-06 | Ordinary readonly review, with two genuinely exposed same-name review candidates and project provenance identifying the accepted root. Retain both locators, the actual selected body/dependencies and completed Core loading before dependent tests. Report the real defect without edits. This combines two checks on the same review route. |
| F-02 | NL-04 | Continue a named saved objective that selects one of two distinct possible tasks. Retain its full read before choosing/editing, the selected workflow's full body and triggered dependencies, the bounded change and verification, plus the delivery stop. The task prompt does not reveal which task the state selects. |
| F-03 | NL-07 | Explicitly select the candidate alias by name and exact locator for readonly planning. Retain its shared planning route and all triggered dependencies from that candidate root; no Desktop operation. |
| F-04 | NL-08 | Explicitly select the candidate Loop by name and exact locator for the identified current objective. Retain the body/current-state reference from the same root and a truthful stop on missing decision input; no ledger/event write or worker launch. |

All four are **NOT_RUN / NOT_AUTHORIZED**. The proposed count is not a permission
request or a reservation of quota. Before any new model work, reconcile the
source-observation prerequisite below and obtain a new bounded launch approval.

## Source and exposure prerequisites

1. Create fresh fixtures under the already selected test root. Copy the exact
   candidate package with its policy/vendor/reference layout; record all paths,
   bytes and modes. Keep the comparison copy, if used, confined to this fixture
   and bind its baseline revision separately. Never update a global install,
   copy credentials, change `HOME`/`CODEX_HOME`, or relax a privacy guard.
2. Fixture project instructions identify one absolute candidate package root
   and the source-layout dependency rules. This binds the accepted source; it
   does not hide global skills or prove OS isolation. For manual cases the
   request includes the exact candidate `SKILL.md` locator as well as its name.
   Do not put expected skill choices or grader outcomes in the natural task
   prompt. Record the instruction bytes separately from grader expectations.
3. Keep all four proposed cases on standalone `codex exec`. Local 0.162.1
   top-level/exec/debug help has no standalone `skills/list` subcommand or
   `exec` startup-catalog output option. The public experimental
   `codex debug prompt-input` renders model-visible input JSON, but is another
   invocation and does not expose `exec --ignore-user-config` in its help.
   Its output is not a same-exec receipt. Only help was inspected; no renderer,
   app-server, thread or model was started for this feasibility check.
4. Offline frontmatter readback proves the fixture's actual bytes and that
   F-01 contains two `code-review` sources. It does not prove model exposure.
   Put acquisition of the missing receipt inside the next approved live case,
   as its first source step, within its single launch and time budget. Through
   the current public terminal tool, read `SOURCE-IDENTITY.json` and run the
   recorded bounded `rg` command over actual skill frontmatter. Retain the
   completed tool result with filenames, names and descriptions. F-01 must
   actually supply both same-name metadata entries to the model before source
   selection/dependent work. A file list or an agent's self-report is insufficient.
5. Classify that tool result as **bounded filesystem discovery**, supported by
   the existing selection contract. It is not a native startup catalog receipt.
   Record native catalog availability/exposure separately as NOT_OBSERVED
   unless the same invocation supplies a verifiable official receipt. These
   cases can test selection after bounded discovery, not native automatic
   duplicate surfacing. If native startup exposure is a required acceptance
   condition, retain the gap and stop at this step; do not redefine it as PASS
   or switch to app-server. This distinction also preserves the original NL-06
   missing evidence rather than claiming a replacement covers more than it does.
6. If the first-step receipt is missing, truncated, inconsistent with source
   bytes, reads an unaccepted body/dependency root, or is not complete by 45
   seconds, stop the case. Do not start later cases before coordinator
   disposition; that launch remains spent. No separate probe model is allowed.
   Retain public events in order and associate complete body/dependency bytes
   with their actual source requests or a verifiable native injection. Compare
   hashes and completion before the first dependent action. Merely finding
   identical text in concatenated outputs cannot attribute a source. Missing
   provenance stays unknown; cross-root reads are not a candidate PASS.

The native app-server `skills/list`/typed-skill schema remains background
capability evidence only. No proposed case selects that entry. No claim is made
that a different command or process exposes the actual initial `exec` input.

Official references for the proposed mechanisms:
[local discovery and invocation](https://learn.chatgpt.com/docs/build-skills),
[CLI prompt-input renderer](https://learn.chatgpt.com/docs/developer-commands?surface=cli#codex-debug-prompt-input).
Version-matched local help bounds the commands used here.

## Concrete standalone execution specification

Private `four-case-specs.json` and each prepared case's `launch-spec.json` retain
the exact absolute argv, prompt bytes/digest, stdin/stdout/stderr paths, fixture
inventory and allowed edits. These fixtures are prepared only: no launch has
occurred. The normalized form below uses `CASE` for that approved exact case
directory, not an unconstrained path selected during execution:

```bash
env PYTHONDONTWRITEBYTECODE=1 TMPDIR="$CASE/tmp" \
  /opt/homebrew/Caskroom/codex/0.162.1/bin/codex \
  --no-daemon --sandbox "$CASE_SANDBOX" --ask-for-approval never \
  -c 'model_provider="openai"' --model gpt-6.1-sol \
  -c 'model_reasoning_effort="medium"' \
  -c "sqlite_home=\"$CASE/state\"" -c "log_dir=\"$CASE/logs\"" \
  --cd "$CASE/project" exec --ignore-user-config --ephemeral --json \
  --skip-git-repo-check - < "$CASE/prompt.txt" \
  > "$CASE/events.jsonl" 2> "$CASE/client-stderr.txt"
```

| Case | Sandbox | Permitted model file edits |
| --- | --- | --- |
| F-01 | `read-only` | None; review source and baseline comparison are fixture-local. |
| F-02 | `workspace-write` | Only `project/app.py`, `project/docs/usage.md`, `project/docs/current-task.md`. |
| F-03 | `read-only` | None; explicit marker plus exact candidate alias locator. |
| F-04 | `read-only` | None; explicit marker plus exact candidate Loop locator. |

Controller/client artifacts use only the corresponding case's `state`, `logs`,
`tmp` and evidence files. Inherited `HOME`/`CODEX_HOME` remain unchanged; ordinary
client initialization/auth I/O can still occur there. Do not copy credentials
or claim all client I/O is technically isolated. `workspace-write` is broader
than the three permitted task files; protect tests/package bytes by instruction
and before/after inventory, without claiming an independent OS restriction.
Case-local TMPDIR keeps new fixture temporary writes under the approved root;
it is not a relocation or rerun of the failed Memory check.

Launch sequentially, at most one invocation per case, no retries or extra
models/agents. The 45-second source deadline is within the 180-second execution
budget. On source failure or the 180-second deadline, interrupt only the owned
case process/session; allow up to 30 seconds to confirm exit. If needed, terminate
only its known owned process group; uncertain exit stops the whole packet with
no restart. Preserve canceled/partial evidence. Do not launch the next case until
the previous process exit and observations are read back.

The proposed four-case controller budget is at most 840 seconds (4 × 210),
excluding offline preparation/review. This is not a token/dollar cap or a promise
that a stalled process exits on time. The public command exposes no verified
per-case monetary/token ceiling here; actual usage and account cost are unknown
until run. Fix model/effort to the stated Sol/medium, retain CLI-reported usage,
stop on quota/access/rate-limit errors, and do not buy credits or change provider.
No new model work or approval request is made by this preparation.

The same invocation can prove that its public tool result exposed fixture
frontmatter and that subsequent exact-source body/dependency reads preceded
actions. It cannot by itself prove an unexposed native startup catalog, absence
of hidden context, all global I/O isolation, or unqualified bare-marker source
resolution. Keep those limits in the case verdict, including when a task succeeds.

## Unchanged blockers and verification scope

The existing full structural check remains FAILED at the unchanged Memory
private-path/privacy-validator interaction. Do not change the guard, move the
test root to evade it, or mix a Memory fix into this packet. The original
focused tests and package parity remain evidence only for their tested scope.

This reassessment changes only the acceptance plan, so check the document diff,
links, unchanged package bytes and retained evidence digests. It does not require
a new broad test run. Earlier independent source review can be reused only for
unchanged source; this revised plan still needs proportionate independent review.
SDS remains APPLICABLE / NOT_RUN for the overall agent-policy diff. The coordinator
has explicitly paused scanning until the candidate correction is settled; do not
start it in this design stage. No commit, push or PR is authorized here.
