# Basic Implementation Example

Use `implementation-slice` when the user asks for a focused change:

```text
Use implementation-slice to add input validation for this parser.
Keep the change scoped, run the parser tests, inspect the diff, and do not commit or push.
```

Expected flow:

1. Read repo policy and parser code.
2. Plan affected files.
3. Implement the smallest change.
4. Run targeted tests.
5. Inspect diff and report evidence.
6. Stop before commit, push, PR creation, release, merge, platform comments, review submissions, or any external write unless the user explicitly authorizes it.
