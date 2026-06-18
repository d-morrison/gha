# d-morrison/gha

Central, reusable GitHub Actions for d-morrison / UCD-SERG / ucdavis R-package
and Quarto repositories. Modeled on
[`r-lib/actions`](https://github.com/r-lib/actions) and
[`easystats/workflows`](https://github.com/easystats/workflows): repos call a
reusable workflow with a tiny stub instead of carrying their own copy.

This repo is **public** so it can be referenced from repositories across the
`d-morrison`, `ucdavis`, `UCD-SERG`, `UCLA-PHP`, and `UCD-IDDRC` owners.

## How it works

Each capability is shipped as two layers:

- **Composite action** (e.g. `check-bibliography-dois/action.yml`) — bundles the
  real steps and any helper script. Referenced as
  `d-morrison/gha/<name>@v1`.
- **Reusable workflow** (`.github/workflows/<name>.yml`, `on: workflow_call`) —
  wraps the composite, declares permissions, and checks out the caller's repo.
  This is what consumer repos target.

A consumer repo adds a small caller stub (see [`examples/`](examples)):

```yaml
name: Check Bibliography DOIs
on:
  push: { branches: [main] }
  pull_request:
  workflow_dispatch:
jobs:
  check:
    uses: d-morrison/gha/.github/workflows/check-bibliography-dois.yml@v1
```

Pin to `@v1` (a moving major tag updated as fixes land). Do not reference
`@main` from consumers.

## Available reusable workflows

| Workflow | Purpose | Key inputs |
|---|---|---|
| `check-bibliography-dois.yml` | Validate book/article BibTeX entries have resolvable DOIs matching CrossRef metadata | `exclude-keys`, `install-quarto`, `no-metadata-check` |
| `check-non-standard-chars.yml` | Detect curly quotes / en–em dashes in `.qmd` and `.R` files | `python-version` |
| `check-links.yml` | lychee link check with bundled config, PR skip-label, and auto-issue on `main` | `lychee-config`, `lychee-args`, `create-issue-on-main`, `skip-label` |
| `summary.yml` | AI summary comment on newly opened issues | — |
| `check-news.yml` | Enforce a `NEWS.md` changelog entry on PRs (wraps `UCD-SERG/changelog-check-action`) | `changelog` |
| `claude.yml` | Agent-mode Claude Code bot: responds to `@claude` mentions, edits files, opens/updates PRs | `setup-r`, `install-quarto`, `use-renv`, `apt-packages`, `pip-packages`, `checkout-submodules`, `link-skills`, `eager-pr`, `prompt-addendum`, `webfetch-allowlist-url`, `reviewer` |
| `claude-code-review.yml` | Read-only Claude PR review (runs the `code-review` plugin; inline findings on `pull_request` runs, consolidated summary on dispatched runs) | `pr-number`, `prompt-addendum`, `checkout-submodules` |

## Permissions

A called reusable workflow cannot hold more `GITHUB_TOKEN` permissions than the
caller grants, and most repos default to a **read-only** token. So workflows
that need to write must have the **caller** grant it on the calling job:

- `check-links` (opens an issue on `main` failures) → grant `issues: write`,
  `pull-requests: read`, `contents: read`.
- `summary` (comments on issues, calls the models API) → grant `issues: write`,
  `models: read`, `contents: read`.
- `check-bibliography-dois`, `check-non-standard-chars` → only `contents: read`
  (the default), so no `permissions:` block is needed.
- `claude` (pushes branches, opens PRs, dispatches the review workflow) → grant
  `contents: write`, `pull-requests: write`, `issues: write`, `id-token: write`,
  `actions: write`, and add the `CLAUDE_CODE_OAUTH_TOKEN` secret.
  - **Optional:** if Claude will edit files under `.github/workflows/`, also add
    a `WORKFLOW_TOKEN` secret (a PAT or GitHub App token with `contents:write` +
    `workflows:write`). The integrated `GITHUB_TOKEN` cannot push workflow-file
    changes — GitHub rejects them without the `workflows` scope. Repos that never
    touch `.github/workflows/` can omit it; pushes fall back to `GITHUB_TOKEN`.
    Note that, unlike `GITHUB_TOKEN`, a PAT/App-token push **does** trigger other
    `push`-based workflows, so enabling `WORKFLOW_TOKEN` can set off extra CI runs.
  - **Optional:** set `checkout-submodules: true` so Claude can read submodule
    contents. Public submodules clone anonymously; private ones additionally need
    a `SUBMODULES_TOKEN` secret.
- `claude-code-review` (read-only review) → grant `contents: read`,
  `pull-requests: write`, `issues: write`, `id-token: write`, and the
  `CLAUDE_CODE_OAUTH_TOKEN` secret.
  - **Optional:** set `checkout-submodules: true` so the reviewer can read
    submodule contents instead of reporting them as uninitialized. Public
    submodules clone anonymously; private ones additionally need a
    `SUBMODULES_TOKEN` secret.

The stubs in [`examples/`](examples) already include the right `permissions:`
blocks — copy them as-is.

The two Claude workflows are a pair: an `@claude review` mention (or any commit
Claude pushes) routes through `claude.yml`, which dispatches `claude-code-review.yml`
via `workflow_dispatch`. Install both, and keep the review stub named
`claude-code-review.yml` (or set `claude.yml`'s `review-workflow-file` input to
match) so the dispatch resolves.

## Versioning

Releases are tagged `vX.Y.Z`; the `vX` major tag moves to the latest compatible
release. Consumers reference `@v1`.

## Notes for private consumers

Reusable workflows in this public repo are callable from public repos
automatically. A **private** consumer must allow access to this repo under
*Settings → Actions → General → Access* before it can call these workflows.

## Scope

This is the pilot set (the byte-identical / near-identical workflow families).
Additional families (spell check, lint-changed-files, pr-commands, R-CMD-check,
publish/preview) may be added later.
