# Issue #145 Memory M0 Threat Model

## Overview

This target-scoped threat model covers the proposed provider-neutral Memory M0
contracts and a future local/manual/CI M1 adapter boundary. The repository is a
public workflow-contract pack; M0 adds offline validators and synthetic public
evidence, not persistence. The primary assets are caller-owned operation
authority, repository/principal/namespace isolation, lifecycle integrity,
idempotency, atomic receipt truth, privacy-safe public artifacts, and the
independent human/platform acceptance boundary.

## Threat Model, Trust Boundaries, And Assumptions

Trust boundaries:

- authoritative current caller/control-plane evidence versus untrusted
  contract documents;
- unchanged V2b eligibility versus M0 operation authority;
- offline authorized-request composition versus future adapter execution;
- future machine-local state versus public Git;
- adapter/database self-report versus independently accepted receipts;
- individual V3-B results versus paired M0/M1 qualification;
- validated evidence versus independent verification, review, acceptance, and
  promotion.

Attacker-controlled inputs include every JSON document, identifier, timestamp,
digest claim, lifecycle link, adapter fingerprint, receipt, synthetic record,
and file path passed to a CLI. Adapter/database output is untrusted. Operator-
controlled inputs include accepted receipt maps, caller-accepted trusted-time
receipts, approved state-root identity, and exact qualified fingerprints. Developer-controlled inputs include public
schemas, validators, fixtures, and evaluation policy.

Assumptions:

- M0 is offline and does not execute a backend;
- future M1 is single-host, current-user, local/manual/CI, default-disabled;
- hostile same-UID processes, distributed coordination, multi-tenant shared
  databases, encryption-at-rest, and confidential/restricted storage are out of
  scope;
- the public repository never stores real operational records or machine-local
  database material.

Security invariants:

- adapter/database data cannot create or accept authority;
- one exact idempotency scope produces at most one applied transition;
- success requires atomic state-plus-receipt durability;
- uncertainty never becomes success;
- every query/operation binds exact repository/principal/namespace/revision/
  path identity;
- memory-off performs zero backend/filesystem touch;
- validation never implies verification, completion, promotion, or permission
  to act.

## Attack Surface, Mitigations, And Attacker Stories

### Authority laundering

An attacker supplies a self-issued receipt, reseals a standalone request, or
backdates freshness. Mitigation: exact caller-owned accepted authority,
eligibility, and trusted-time inputs remain separate; request and receipt
validation reconstruct the full chain and preserve expiry/nonce/state-root.

### Cross-scope disclosure or mutation

An attacker reuses a valid-looking request across repositories, principals,
namespaces, revisions, or paths. Mitigation: exact identity equality at every
stage, digest binding, negative isolation tests, and generic non-disclosing
errors.

### Replay and double execution

An attacker repeats or alters an idempotency key. Mitigation: bind key to the
complete scope/operation/target/candidate identity; exact replay returns the
original result, and conflicting replay rejects.

### Crash-window receipt forgery

An adapter claims success after state or receipt committed alone. Mitigation:
`applied` requires one atomic transaction and exact pre/post/transaction
bindings; timeout, interruption, lock, disk, integrity, or commit uncertainty
is failure. M0 receipt validation is not proof that a transaction occurred.

### Schema/capability drift

A changed adapter, schema, tokenizer, platform, or SQLite runtime reuses prior
qualification. Mitigation: exact fingerprint binding, fail-closed mismatch,
no automatic migration, and M1 requalification.

### Sensitive-data capture and error echo

Malicious or accidental content includes credentials, PII, private paths, raw
logs, or runtime details. Mitigation: public/internal-only closed fields,
defense-in-depth pattern rejection, generic errors, explicit public placement,
and synthetic fixtures only.

### Parser and resource abuse

Inputs use duplicate keys, deep/large objects, extreme integers, symlinks,
special files, or changing files. Mitigation: strict bounds, integer-only JSON,
no-follow regular-file snapshots, canonical digests, and bounded output.

### Qualification laundering

A memory-on result changes V3-B policy/verifier, replays an M1 receipt across
fingerprints, or claims efficacy. Mitigation: paired validation includes the
canonical verifier assignment and a strict M1 receipt bound to the exact
qualification/V3-B/fingerprint/safety/execution tuple. Evals exercise valid
reseals and replay and derive security metrics from observed outcomes.

### Destructive lifecycle escalation

A logical delete or expiry is treated as purge authority. Mitigation: physical
purge is unsupported; retention never authorizes deletion; later M1 needs a
separate destructive/recovery decision.

Existing repository mitigations include strict released V2b/V2d/V3 validators,
exact false-authority fields, generic non-echoing CLI errors, synthetic-only
public fixtures, the tracked Python resolver, and review/readiness gates.

## Severity Calibration (Critical, High, Medium, Low)

- **Critical:** a path allowing adapter/database self-authorization followed by
  cross-scope mutation, or public storage of real credentials/private records.
- **High:** double execution, forged atomic success, cross-repository/principal
  disclosure, or a qualification result that grants promotion/activation.
- **Medium:** schema drift accepted without requalification, sensitive values
  echoed in errors, or memory-off touching an ambient backend path without a
  demonstrated mutation.
- **Low:** bounded deterministic metadata inconsistency that fails closed,
  exposes no private content, performs no action, and cannot alter authority or
  qualification status.

Out-of-scope attacker stories include hostile same-UID interference, physical
device compromise, shared-host confidentiality, cross-host replication, and
network/provider attacks because M0 has no backend/network and M1 would require
a new reviewed envelope for those conditions.

Repository: sha256:a409ff64b9cef22b1ad14b6a00659e99606a3702f40f6e5eb81e4ae4da887bbd
Version: 47d1178a8fcabaa5ca23af15e615aa0eaf9d7257
