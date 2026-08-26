# Merge Review Report

## Merge Readiness

READY | BLOCKED | NEEDS HUMAN DECISION

## Base And Head

- Repository:
- Pull request number and URL:
- Pull request state/draft/mergeable:
- Base SHA:
- Head SHA:
- Merge-base SHA:
- Diff digest:
- Review mode: `merge-review | merge-review-deep`
- Pre-commit evidence reused and applicability rationale:

## DoD Alignment

## Blocking Findings

## Non-blocking Findings

## Verification Evidence

- Required hosted CI name/run ID/head SHA/conclusion:
- Required CI policy source/reference/exact required-name set:
- Security Diff Scan scope/source revision/result when required:
- Unresolved review threads:

## Finding Dispositions

- Finding ID/severity/disposition/evidence:

## Platform Receipt Readback

- Contract: `exact-head-merge-review/v1`
- Receipt ID and URL:
- Receipt digest:
- Receipt body is complete strict JSON; digest scope verified (not Markdown scraping):
- Connector readback time:
- Validation result:
- Receipt authority: `advisory_review_evidence`
- Merge authorized: `false`

## Hosted Exact-Head Gate (when configured)

- Contract: `exact-head-merge-readiness/v2`
- Receipt sequence (positive, bounded, and greater than the prior exact-head receipt):
- Check context: `Exact-Head Merge Readiness`
- Check run ID / details URL:
- Dedicated GitHub App ID / slug:
- Check head SHA equals live PR head:
- Gate workflow/run identity:
- Upstream CI excludes this gate:
- Gate conclusion and final drift readback:

## Release-State Classification (when release-sensitive)

- Repository source/package version:
- Candidate preparation:
- GitHub tag/Release publication truth:
- Active guidance:
- Historical point-in-time records:
- Transition safety after successful publication:
- Pre-mutation preview/conflict checks:
- Post-mutation platform readback (only after separately authorized actions):

## Residual Risk

## Required Human Gate

The receipt and hosted gate record evidence only. State the separate merge
authority or human decision still required.
