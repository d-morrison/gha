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
| `check-phi.yml` | Scan PRs (added lines only) for content that looks like PHI — SSNs, medical record numbers, dates of birth, PHI column headers in data files | `detectors`, `paths-ignore`, `allowlist-file`, `fail` |
| `check-links.yml` | lychee link check with bundled config, PR skip-label, and auto-issue on `main` | `lychee-config`, `lychee-args`, `create-issue-on-main`, `skip-label` |
| `summary.yml` | AI summary comment on newly opened issues | — |
| `check-news.yml` | Enforce a `NEWS.md` changelog entry on PRs (wraps `UCD-SERG/changelog-check-action`) | `changelog` |
| `claude.yml` | Agent-mode Claude Code bot: responds to `@claude` mentions, edits files, opens/updates PRs | `setup-r`, `install-quarto`, `use-renv`, `apt-packages`, `pip-packages`, `checkout-submodules`, `link-skills`, `eager-pr`, `prompt-addendum`, `webfetch-allowlist-url`, `reviewer` |
| `claude-code-review.yml` | Read-only Claude PR review (runs the `code-review` plugin; inline findings on `pull_request` runs, consolidated summary on dispatched runs) | `pr-number`, `prompt-addendum`, `checkout-submodules` |
| `quarto-publish.yml` | Render a Quarto site and deploy it to GitHub Pages | `path`, `setup-r`, `r-packages`, `use-renv`, `tinytex`, `apt-packages`, `output-dir`, `checkout-submodules`, `pre-render-artifact`, `pre-render-artifact-path`, `deploy` |

## Permissions

A called reusable workflow cannot hold more `GITHUB_TOKEN` permissions than the
caller grants, and most repos default to a **read-only** token. So workflows
that need to write must have the **caller** grant it on the calling job:

- `check-links` (opens an issue on `main` failures) → grant `issues: write`,
  `pull-requests: read`, `contents: read`.
- `summary` (comments on issues, calls the models API) → grant `issues: write`,
  `models: read`, `contents: read`.
- `check-bibliography-dois`, `check-non-standard-chars`, `check-phi` → only
  `contents: read` (the default), so no `permissions:` block is needed.
- `quarto-publish` (deploys to GitHub Pages) → grant `pages: write`,
  `id-token: write`, `contents: read`, and set Settings → Pages → Source =
  "GitHub Actions" once. Build-only callers (`deploy: false`) need just
  `contents: read`.
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

## PHI scanning (`check-phi`)

`check-phi` is a **heuristic tripwire, not a HIPAA compliance tool.** It flags
patterns that should almost never be committed — US Social Security numbers,
medical record numbers, dates of birth, and PHI-suggestive column headers in
delimited data files (`.csv`/`.tsv`/`.psv`) — so a human reviews before the
data merges. It is tuned for high precision (few false positives), so it will
miss free-text PHI such as patient names. The `phone` and `email` detectors
exist but are **off by default** (too noisy in source); enable them via the
`detectors` input.

- **Diff-scoped on PRs.** Only lines *added* by the PR are scanned, so existing
  fixtures don't re-trip the check on unrelated edits. `push` runs scan the
  whole tracked tree (`git ls-files`).
- **Values are never printed.** A leaked identifier in a CI log is still a leak,
  so findings report only `file:line:col` and the detector name — never the
  matched text. Findings appear as inline annotations on the PR.
- **Suppressing false positives** (e.g. synthetic test data): add a `phi-allow`
  comment on the line, or list a regex matching the value in an allowlist file
  (defaults to `.github/phi-allowlist.txt` when present; override with the
  `allowlist-file` input). Use `fail: false` to downgrade to warnings.

## Versioning

Releases are tagged `vX.Y.Z`; the `vX` major tag moves to the latest compatible
release. Consumers reference `@v1`. See [`CHANGELOG.md`](CHANGELOG.md) for what
changes as the `@v1` tag moves and for any breaking-change migration steps.

## Reverse dependencies

[`REVDEPS.md`](REVDEPS.md) tracks repos that call these workflows, so consumers
can be notified before a breaking change. If your repo uses `gha`, please add
it there.

## Notes for private consumers

Reusable workflows in this public repo are callable from public repos
automatically. A **private** consumer must allow access to this repo under
*Settings → Actions → General → Access* before it can call these workflows.

## Scope

This is the pilot set (the byte-identical / near-identical workflow families).
Additional families (spell check, lint-changed-files, pr-commands, R-CMD-check,
publish/preview) may be added later.
