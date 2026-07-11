# Loop Engineering V2a: Heterogeneous Subagent Routing

## Objective

Deliver an independently adoptable Loop Engineering V2a increment that classifies
task capability needs, selects an auditable custom-agent role/profile, degrades
safely when runtime mappings are unavailable, and records routing/integration
evidence without changing V1 permissions, scope, human gates, or completion rules.

GitHub issue: <https://github.com/jeffery777/codex-dev-skills/issues/85>

## Source Of Truth

- Repository policy: `AGENTS.md`
- GitHub scope and acceptance criteria: issue `#85`
- This loop spec
- Implementation plan: `docs/loops/issue-85/implementation-plan.md`
- Official Codex subagent/custom-agent documentation
- Current branch, Git diff, tests, evals, review artifacts, and accepted GitHub state

Goal status, worker summaries, runtime mappings, and chat summaries are progress or
coordination evidence only.

## In Scope

- deterministic capability-neutral classification over the nine requested factors;
- minimal fast explorer, balanced worker, deep reviewer, and security reviewer roles;
- repo-owned, namespaced custom-agent profiles on the public Codex configuration surface;
- runtime mapping preflight and safe same-class/parent/sequential/human-gate fallback;
- route, worker, and main-agent integration receipts;
- opt-in user/project adoption, installer/catalog integration, docs, tests, and evals;
- formal code/docs/security/deep-merge review and PR-readiness evidence.

## Out Of Scope

- V2b external persistent memory and V2c memory/code-intelligence backends;
- provider orchestration services, schedulers, daemons, sidecars, private Desktop state,
  app-server clients, UI scraping, or reverse-engineered endpoints;
- writing actual user or project agent configuration during this delivery task;
- changing another repository, release metadata, tags, releases, deploys, or merge;
- unrelated refactors or legacy Desktop wrapper cleanup.

## Architecture And Authority

1. V1 remains the workflow, authority, protected-history, claim, gate, and completion core.
2. V2a adds a deterministic classification and role-routing layer whose outputs are
   advisory execution choices, never permission or completion authority.
3. Shared semantics use capability classes, not permanently-current model IDs.
4. Concrete model/reasoning mappings live only in replaceable runtime profile metadata.
5. Custom-agent files use namespaced identities and the documented standalone TOML schema.
6. The routing and integration evidence chain binds factors, selected class/role,
   mapping/fallback, scope/ownership, source revision, worker receipt, and
   main-agent disposition in their actual execution order.
7. Invalid, stale, partial, conflicting, or unverifiable receipts cannot prove completion.
8. No safe degradation for a high-risk task results in a human gate.

## Definition Of Done

- V2a classification, roles, runtime boundary, preflight, fallback, and receipts are implemented.
- Model/profile changes cannot expand mutation, sandbox, external-write, or gate authority.
- Tests/evals cover requested route and failure modes with deterministic production behavior.
- User-level and project-scoped adoption, runtime limits, rollout, fallback, and rollback are documented.
- Installer/profile validation passes in isolated temporary environments without modifying real config.
- All MUST-FIX findings are closed; SHOULD-FIX/NIT findings are fixed or durably dispositioned.
- Security diff scan, deep merge review, and merge-readiness gate complete against the final diff.
- Issue, branch, commit, remote branch, and ready-for-review PR are traceable and the PR is not merged.

## Verification

```bash
git diff --check
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
```

## Threat And Risk Analysis

- Reject unknown profile keys, unsafe sandbox widening, path/symlink traversal, and unsafe overwrite.
- Treat model/reasoning availability as runtime capability, not a permanent repository guarantee.
- Detect profile-name collisions instead of guessing user/project same-name precedence.
- Bind receipts to source/profile/scope identity and reject stale, partial, failed, or conflicting output.
- Keep high-risk/security triggers non-compensatory so cheap/fast preferences cannot downgrade them.
- Never infer external-write authority from a role, model, receipt, worker, or runtime capability.
- Do not claim latency/token/cost improvement without measurements; evals report proxies only.

## Rollout And Rollback

Roll out by first landing shared classification/receipt semantics, then explicitly installing
the opt-in profile group at user or trusted-project scope after preflight. Roll back by
running `./install.sh diff codex-agent-profiles` and then
`./install.sh uninstall codex-agent-profiles --yes`. Project-scoped rollback
must reuse the same `CODEX_CUSTOM_AGENTS_DIR` and
`CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES` values as installation. Uninstall
refuses modified profiles and performs a complete pre-delete check, so preserve
and reconcile local changes before retrying. Reverting the V2a commit is the
source-level rollback; V1 sequential/shared semantics remain usable throughout.

## Human Gates

Stop for product/source ambiguity, scope expansion, destructive action, unsafe permission or
public-contract changes, insufficient high-risk verification, unsupported private runtime
integration, unresolvable profile collision, external writes outside the authorization in
the issue prompt, merge, release, tag, deploy, or final independent merge approval.
