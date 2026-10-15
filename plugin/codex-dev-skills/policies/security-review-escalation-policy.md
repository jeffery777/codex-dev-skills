# Security Review Escalation Policy

Routine code review should include baseline security checks. Escalate to deep review when the change touches:

- credentials or private keys
- permissions, identity, or tenant boundaries
- sensitive user data
- payments or billing
- file upload or parsing
- external APIs
- migrations or persistent data
- deployment or infrastructure
- dependency supply chain
- cryptography or randomness

Escalated review should check source-to-sink flow, failure modes, rollback, logging, and whether verification evidence is strong enough for the risk.
