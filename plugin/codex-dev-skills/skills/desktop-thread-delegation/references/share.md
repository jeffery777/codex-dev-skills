# Immutable Thread Sharing

Sharing is a privacy-sensitive disclosure action, not delegation. Use
`share_thread` only after an explicit user request, exact-target validation,
audience preview, and sensitive-content review.

1. Inspect the active callable and identify exact `threadId` and preferred
   `hostId` when supplied. Establish the account/workspace audience from current
   public product context; if unknown, stop.
2. Require the user to confirm review of the complete thread through the public
   UI or another complete exposed view. Reuse that confirmation when already
   given for this exact snapshot. Recent, truncated, or paginated agent reads
   alone are not complete review.
3. Inspect available content for credentials, private paths, customer/incident
   data, unpublished vulnerability details, and other sensitive material even
   if the runtime redacts known secret patterns. If complete review cannot be
   established or sensitive content may remain, stop before link creation.
4. Call only within that reviewed and authorized scope. Report exact target,
   audience classification/source, complete-review confirmation/coverage, and
   the immutable snapshot result. Later thread changes do not update the link.

Link creation, link delivery, revocation, and repository completion are separate
states. The current callable exposes no revoke operation; direct the user to
ChatGPT data controls for review or revocation. Never claim automatic rollback.
If schema or behavior changes, revalidate the affected boundary before acting.
