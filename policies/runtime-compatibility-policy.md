# Runtime Compatibility Policy

Every public skill and workflow must state runtime compatibility.

## Shared

Shared workflows must work through repository files, shell/git inspection, and durable artifacts. They may mention Desktop or CLI examples but cannot require Desktop-only behavior.

## CLI

CLI workflows must provide a Desktop fallback when practical.

## Desktop

Desktop workflows must label main-agent or worker-delegation behavior as Desktop-only and provide a CLI fallback when practical.

## Plugin-dependent

Plugin-dependent workflows must name the required plugin or connector and define a fallback when unavailable.
