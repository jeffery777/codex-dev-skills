# Issue #209 Threat Model

The pilot accepts only one trimmed line of at most 512 UTF-8 bytes and applies
the existing V2b sensitivity/provenance rules plus lexical rejection for chat
role markers, log-line markers, credentials, PII, private/absolute paths, and
configuration assignments before backend access. These controls reduce the
accepted surface but are not a general content-classification or DLP system;
callers remain responsible for supplying only verified minimal project facts.
Raw FTS/SQL is unavailable because only the existing structured M1 query is
used. Expired authority, scope/revision/evidence drift, replay, tampering,
schema/FTS unavailability, and identity drift fail closed through the unchanged
contracts. Shared hosts, encryption claims, physical purge, and external
services are out of scope.
