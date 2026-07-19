# P2 Adapter Main-Agent Verification

The main agent independently inspected and exercised the worker output. During
integration it found and fixed two issues before acceptance:

1. the resolved npm entry used `#!/usr/bin/env node`, but the bounded environment
   removed `PATH`, so live qualification exited 127;
2. the fixture's expected vector provider did not match current GitNexus 1.6.9
   schema-5 metadata, so the first production-controller refresh correctly
   failed closed as capability drift.

The final implementation binds and directly invokes the resolved Node runtime,
revalidates runtime/entry identities and the canonical qualification
fingerprint, and binds the observed schema-5 capability policy. A new unit test
covers runtime discovery/invocation/drift.

Independent evidence:

- focused adapter tests: 21/21 passed;
- production preflight: GitNexus 1.6.9, resolved-symlink policy, bound runtime,
  fingerprint `8106875b9184184ca7a7a8c788d6799f3c1c55ac72821f5a3a54893506da176d`;
- production-controller isolated refresh: `refreshed`,
  `qualified-index-adoptable`, indexed revision matched expected HEAD;
- tracked-state digest before/after:
  `f71ff4c3c53ba19931bb8f314824bd5cc010c5088a27fb2e037c394fd0453183`;
- automatic refresh authority remained false.

Disposition: accepted as bounded implementation output after main-agent fixes;
not accepted as objective completion or publication authority.
