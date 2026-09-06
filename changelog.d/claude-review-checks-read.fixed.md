- `claude-code-review`: the `claude-review` job now requests `checks: read`,
  and the README, website, and example caller stub tell callers to grant it.
  `actions: read` covers workflow runs but not `GET .../commits/{ref}/check-runs`,
  so the reviewer's check-status reads failed with HTTP 403
  and a clean diff was reported as blocked on human review (ucdavis/bcs#964, #829).
