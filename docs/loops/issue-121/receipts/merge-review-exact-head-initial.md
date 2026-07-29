# Issue #121 Initial Exact-Head Merge Reviews

Date: 2026-07-29

## Candidate

- Pull request: <https://github.com/jeffery777/codex-dev-skills/pull/122>
- Base: `845c768ca6a8b0c6d8591a79aa5101c0dd12bd17`
- Reviewed head: `8d08d1823b986e047c43a321ae637decd88b6084`
- Working tree: clean

## Results

The final deep code review, documentation review, and security/privacy
re-review independently reported the same single MUST-FIX:

- the ledger source was the implementation commit
  `d498d3a314b47e7c6128f0ac4f4130b4e6f7765c`;
- the PR head was the authorized ledger-only descendant
  `8d08d1823b986e047c43a321ae637decd88b6084`;
- the ledger remained active, so the production source validator correctly
  rejected the ancestor relation.

No review found another code, public-contract, validator, fail-closed,
authority, fixture, eval, documentation, security, or privacy issue.
Security reported zero vulnerabilities.

The documentation review additionally requested that the historical review
disposition identify its authorization boundary as point-in-time evidence.

## Verification

- focused operational-evidence tests: 44 passed;
- operational-evidence eval: 12/12 passed;
- full repository suite: 796 passed;
- Loop Engineering eval: 23/23 passed;
- external-memory eval: 31/31 passed;
- shell syntax and base-to-head diff hygiene: passed.

## Disposition

Merge readiness was blocked. The accepted resolution is the existing
contract's terminal ancestor rule: apply the independently authorized
`P4-readiness` completion and terminal objective event, commit that ledger
state, rerun production repository validation on the new exact head, and
repeat every formal merge review before commenting or merging.
