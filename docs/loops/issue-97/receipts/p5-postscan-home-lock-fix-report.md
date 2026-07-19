# P5 Post-Scan Isolated-Home Lock Fix Worker Report

Status: complete within assigned scope; no commit, push, or external write.

Implemented:

- a device/inode-keyed process-local and cross-process lock serializes one
  isolated home across repository controllers;
- the verified home directory descriptor, home lock, and repository lock span
  the complete refresh lifecycle;
- emptiness is checked under the home lock and again immediately before the
  runner; post-run identity is rebound before adoption;
- timeout, unsafe-lock, same-inode contamination, and cross-process reuse
  regressions were added.

Worker verification: the complete adapter suite passed 79/79 and owned-file
diff checking passed. Main-agent verification remains the integration authority.
