# P1 Main-Agent Verification

The main agent independently inspected the installed GitNexus 1.6.9 command,
metadata, extension-loader, staleness, query, index-only, registry, and Git
exclude implementations and confirmed:

- executable discovery resolves an npm symlink to a regular executable entry;
- version/help flags match the qualification receipt;
- current package metadata uses primary `gitnexus.json`, legacy mirror/fallback,
  and incremental schema `5`, while the existing stale index is legacy schema `1`;
- GitNexus staleness helpers can return not-stale on Git errors, so the adapter
  must derive freshness independently;
- analyze-specific extension policy can attempt installation unless explicitly
  forced offline;
- index-only suppresses context/skill injection but still writes derived index,
  registry, and possibly `.git/info/exclude`.

The main agent then completed live isolated Mac evidence recorded in
`gitnexus-1.6.9-qualification.md`: the initial unsafe side effects were detected
and treated fail closed; a later offline, isolated, exclusion-preconditioned
index-only refresh preserved complete tracked/protected and Git-local digests.

Disposition: accepted as defensive design evidence. No completion is proven;
the implementation and negative tests must satisfy these controls and undergo
fresh formal security review.
