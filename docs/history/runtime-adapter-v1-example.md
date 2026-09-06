# Historical Runtime Adapter V1 Example

Historical, non-executable record migrated from the active runtime-boundary
example for issue #223. Every helper and helper-shaped JSON contract below is
retired. These examples are not current callables, scripts, supported schemas,
or instructions to rebuild a wrapper. Do not execute them or use their status
values as current capability or authority evidence.

Use [the active native example](../../examples/runtime-adapter-boundary.md) and
the current exposed callable. The [retirement record](../desktop-runtime-wrapper-v1-deprecation.md)
explains removal. The following material is preserved only to interpret old
records; its future-tense wording describes the retired design.

## Minimal Caller-Supplied Capability Metadata

A non-state-changing helper may normalize metadata the caller already supplied, but it must not gather that metadata by scanning Desktop files or calling thread tools. This example is evidence only; it does not open, fork, message, continue, or read a Desktop thread.

```json
{
  "requested_action": "normalize-runtime-capability-metadata",
  "metadata_source": {
    "source": "runtime-reported schema",
    "contract_version": "version unavailable",
    "last_verified": "YYYY-MM-DD",
    "available": true
  },
  "capabilities": [
    {
      "action": "read-thread",
      "tool_or_api": "read_thread",
      "classification": "read-only",
      "request": {
        "required": ["threadId"],
        "optional": [
          "hostId",
          "turnLimit",
          "cursor",
          "includeOutputs",
          "maxOutputCharsPerItem"
        ]
      },
      "response": {
        "required": ["status", "threadId"],
        "errors": ["runtime-provided error"]
      },
      "source": "runtime-reported schema",
      "contract_version": "version unavailable",
      "last_verified": "YYYY-MM-DD"
    }
  ]
}
```

If the caller cannot supply the action classification, required request fields, minimum response fields, source, contract version or `version unavailable`, and `last_verified`, the helper should return `stopped` or `unavailable` rather than filling gaps from private runtime state.

The planner may consume that normalized discovery output as caller-supplied `capability_evidence`. This still does not open, fork, message, continue, or read a Desktop thread:

```json
{
  "action": "plan-thread-action",
  "target_action": "read-thread",
  "capability_evidence": {
    "status": "available",
    "capabilities": [
      {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["threadId"],
        "optional_request_fields": [
          "hostId",
          "turnLimit",
          "cursor",
          "includeOutputs",
          "maxOutputCharsPerItem"
        ],
        "minimum_response_fields": ["status", "threadId"],
        "error_response_fields": ["runtime-provided error"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": "YYYY-MM-DD",
        "discovery_helper_version": "0.1.0"
      }
    ]
  },
  "target": {
    "repo": "owner/name",
    "remote": "origin URL",
    "branch": "branch-name",
    "thread_id": "thread identifier supplied by caller"
  },
  "prompt": {
    "summary": "Read documented thread metadata.",
    "body": "Prepare read-only evidence only; do not call Desktop private runtime state."
  },
  "boundaries": {
    "in_scope": ["docs/runtime-adapter-v2.md"],
    "out_of_scope": [".work/", "Desktop private runtime state"],
    "external_writes_blocked": true
  },
  "authorization": {
    "thread_action_authorized": false,
    "external_write_authorized": false
  }
}
```

If the target action is missing from `capability_evidence`, the planner returns a CLI-compatible fallback. If the classification is mismatched, the request or response shape is unclear, or the evidence points at forbidden Desktop runtime sources, the planner stops.

## Minimal Contract Comparison Evidence

Before relying on a runtime, connector, schema, or documentation change, compare the old wrapper contract evidence with the newer normalized capability evidence. This example is evidence only; it does not authorize or call a Desktop thread tool.

```json
{
  "requested_action": "compare-runtime-contract-evidence",
  "target_action": "read-thread",
  "old_contract": {
    "action": "read-thread",
    "tool_or_api": "read_thread",
    "classification": "read-only",
    "required_request_fields": ["threadId"],
    "minimum_response_fields": ["status", "threadId"],
    "capability_source": "active tool list",
    "contract_version": "version unavailable",
    "last_verified": "YYYY-MM-DD"
  },
  "new_capability_evidence": {
    "status": "available",
    "capabilities": [
      {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["threadId"],
        "optional_request_fields": [
          "hostId",
          "turnLimit",
          "cursor",
          "includeOutputs",
          "maxOutputCharsPerItem"
        ],
        "minimum_response_fields": ["status", "threadId"],
        "error_response_fields": ["runtime-provided error"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": "YYYY-MM-DD",
        "discovery_helper_version": "0.1.0"
      }
    ]
  }
}
```

The comparison should return `compatible` only when the tool/API name, classification, required request fields, and minimum response fields still match. It should return `fallback` when the capability is missing or unavailable, and `stopped` when required request fields, minimum response fields, classification, tool/API name, or source evidence changed or points at forbidden private runtime sources. State-changing actions such as `create-thread` may be compared as contract evidence, but the comparison does not call or authorize `create_thread`.

## Minimal Create-Thread Preflight Evidence

Before a future `create_thread` runtime call, a non-state-changing preflight helper can check whether the evidence is ready. This is not a runtime-call path. It does not open a thread, call `create_thread`, read Desktop private runtime state, or authorize commit, push, PR creation, merge, or other external writes.

```json
{
  "requested_action": "preflight-create-thread-runtime-call",
  "target_action": "create-thread",
  "target": {
    "repo": "owner/name",
    "remote": "origin URL",
    "branch": "branch-name",
    "expected_head": "commit SHA expected by the caller"
  },
  "prompt": {
    "summary": "Prepare a bounded Desktop thread prompt.",
    "body": "Read repo files first, do the scoped task, run tests, and report evidence."
  },
  "capability_evidence": {
    "status": "available",
    "capabilities": [
      {
        "action": "create-thread",
        "tool_or_api": "create_thread",
        "classification": "state-changing",
        "required_request_fields": ["prompt", "target"],
        "adapter_required_fields": ["title"],
        "optional_request_fields": [
          "title",
          "model",
          "thinking",
          "target.environment.startingState"
        ],
        "minimum_response_fields": [
          "threadId plus hostId, or clientThreadId"
        ],
        "error_response_fields": ["runtime-provided error"],
        "capability_source": "active tool list",
        "contract_version": "version unavailable",
        "last_verified": "YYYY-MM-DD",
        "discovery_helper_version": "0.1.0"
      }
    ]
  },
  "contract_comparison": {
    "status": "compatible",
    "target_action": "create-thread",
    "contract_comparison": {
      "compared_fields": [
        "action",
        "tool_or_api",
        "classification",
        "required_request_fields",
        "minimum_response_fields"
      ],
      "old_contract": "old create-thread contract evidence",
      "new_capability": "new normalized create-thread capability evidence"
    }
  },
  "boundaries": {
    "in_scope": ["durable repo files or task scope"],
    "out_of_scope": [".work/", "Desktop private runtime state"],
    "external_writes_blocked": true
  },
  "authorization": {
    "thread_action_authorized": true,
    "authorized_thread_action": "create-thread",
    "external_write_authorized": false
  }
}
```

The preflight result may be `ready`, `fallback`, or `stopped`. `ready` means only that evidence is complete for a future separately approved runtime call. Use `fallback` for missing or unavailable capability/comparison evidence or missing exact thread-action authorization; use `stopped` for incompatible or unclear contract evidence, classification mismatch, missing repo/remote/branch/expected-head evidence, forbidden private source hints, or external-write requests.

## Minimal Read-Thread Preflight Evidence

Before a future read-only `read_thread` runtime call, a non-state-changing preflight helper can check whether the evidence is ready. This is not a runtime-call path. It does not read a thread, call `read_thread`, read Desktop private runtime state, treat preflight as runtime-call authorization, or authorize commit, push, PR creation, merge, or other external writes.

```json
{
  "requested_action": "preflight-read-thread-runtime-call",
  "target_action": "read-thread",
  "target": {
    "repo": "owner/name",
    "remote": "origin URL",
    "branch": "branch-name",
    "thread_id": "thread identifier supplied by the caller"
  },
  "read_request": {
    "summary": "Check read-only thread evidence readiness.",
    "expected_fields": ["status", "threadId"]
  },
  "capability_evidence": {
    "status": "available",
    "capabilities": [
      {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["threadId"],
        "optional_request_fields": [
          "hostId",
          "turnLimit",
          "cursor",
          "includeOutputs",
          "maxOutputCharsPerItem"
        ],
        "minimum_response_fields": ["status", "threadId"],
        "error_response_fields": ["runtime-provided error"],
        "capability_source": "active tool list",
        "contract_version": "version unavailable",
        "last_verified": "YYYY-MM-DD",
        "discovery_helper_version": "0.1.0"
      }
    ]
  },
  "contract_comparison": {
    "status": "compatible",
    "target_action": "read-thread",
    "contract_comparison": {
      "compared_fields": [
        "action",
        "tool_or_api",
        "classification",
        "required_request_fields",
        "minimum_response_fields"
      ],
      "old_contract": "old read-thread contract evidence",
      "new_capability": "new normalized read-thread capability evidence"
    }
  },
  "boundaries": {
    "in_scope": ["durable repo files or task scope"],
    "out_of_scope": [".work/", "Desktop private runtime state"],
    "external_writes_blocked": true
  },
  "authorization": {
    "thread_action_authorized": false,
    "external_write_authorized": false
  }
}
```

The preflight result may be `ready`, `fallback`, or `stopped`. `ready` means only that evidence is complete for a future separately approved read-only runtime call. Use `fallback` for missing or unavailable capability/comparison evidence; use `stopped` for incompatible or unclear contract evidence, classification mismatch, missing repo/remote/branch/thread-id evidence, missing expected fields, forbidden private source hints, attempts to treat preflight as runtime-call authorization, or external-write requests.

## Retired End-To-End Evidence Pipeline

The former V1 pipeline and its component helpers have been removed. This
section preserves only the non-executable concepts needed to understand the
historical boundary; it does not identify retained fixtures or an available
helper path. Use the
[native capability contract](../native-runtime-capabilities.md) and the
current runtime's documented callable instead. The
[retirement record](../desktop-runtime-wrapper-v1-deprecation.md) provides
historical context and does not authorize reconstructing or reactivating the
removed helpers.
