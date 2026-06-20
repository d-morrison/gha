# Changelog

All notable changes to `d-morrison/gha` are documented here.

This repo uses a **moving major tag** (`v1`) for consumers, following the
[`r-lib/actions`](https://github.com/r-lib/actions) convention: the `v1` tag
moves forward as non-breaking fixes land, and consumers pin to `@v1`. Each
release is also tagged with a full `vX.Y.Z` so a specific point can be pinned
if needed. Breaking changes bump the major tag (`v2`, …) and are called out
below with migration steps.

## [Unreleased]

### Added

- `quarto-publish` — render a Quarto site and deploy it to GitHub Pages. A
  composite (`quarto-publish/action.yml`) sets up Quarto (optionally R/renv and
  TinyTeX), renders a project at a given `path`, and stages the rendered output
  (`<path>/<output-dir>`, default `_site`) as a Pages artifact. The reusable
  workflow (`quarto-publish.yml`) adds the deploy, optional submodule init, and
  a `pre-render-artifact` input so a caller can inject build-time assets (e.g.
  recorded media) before render. First consumer: `Lacaedemon/sparta` (#37).
- PR-preview / publish family (#33) — centralizes the three-workflow preview
  pipeline rme carried inline:
  - `preview` composite action + `preview.yml` reusable workflow — build half;
    renders the Quarto site read-only in the (possibly fork) PR context and
    uploads it + PR metadata as an artifact. Parameterized for non-rme
    consumers (R version, apt packages, renv on/off, local-package install,
    Chrome, submodules, render profile). Writes PR metadata **after** checkout
    so `git clean -ffdx` can't wipe it from the artifact (d-morrison/rme#913),
    and keeps the `preview:pdf`/`preview:docx`/`preview:revealjs` and
    `clear freezer` label gates.
  - `preview-deploy.yml` reusable workflow — deploy half; on `workflow_run`
    completion publishes the artifact to `gh-pages` in the base-repo context
    and comments the preview link. Kept split from the build half so untrusted
    fork code never holds write permissions (the trust boundary).
  - `cleanup-pr-previews.yml` reusable workflow — scheduled housekeeping that
    deletes preview directories for closed PRs.
- `check-phi` — scans pull requests (added lines only; whole tree on `push`)
  for content that looks like PHI: US Social Security numbers, medical record
  numbers, dates of birth, and PHI-suggestive column headers in delimited data
  files. Matched values are never printed to the log; false positives are
  suppressed via a `phi-allow` line comment or a regex allowlist file. The
  `phone`/`email` detectors are available but off by default.
- `CHANGELOG.md` (this file) — records what changes as the `@v1` tag moves, so
  consumers can see what they picked up.
- `REVDEPS.md` — tracks repos that consume these workflows so breaking changes
  can be announced. See the file for how to register.
- `.github/actions/checkout-submodules` composite action — centralizes the
  submodule-init logic (the `SUBMODULES_TOKEN` `insteadOf` rewrite and the
  anonymous-clone fallback) shared by the `claude` and `claude-code-review`
  reusable workflows (#25).

### Changed

- Multi-line `run:` blocks in the composite actions and reusable workflows now
  declare `set -euo pipefail` explicitly. GitHub already runs `shell: bash`
  with `-eo pipefail`; the net new protection is `nounset` (unset-variable
  typos now fail fast), plus consistency with the rest of the script logic.
- `claude` and `claude-code-review` no longer carry duplicate `Checkout
  submodules` steps; both call the shared `checkout-submodules` action instead,
  so the token-rewrite logic lives in one place (#25).
- `check-bibliography-dois` now collects `.bib` files NUL-delimited into a bash
  array, so bibliography paths containing spaces are passed to the checker as
  intact single arguments instead of word-splitting (#30).
- `claude-code-review`'s prompt now instructs the reviewer to watch for AI
  hallucinations — fabricated functions/arguments/APIs, invented references,
  DOIs, or URLs, plausible-but-unreal file paths and constants, and comments
  that describe behavior the code doesn't implement — and to verify questionable
  symbols against the codebase rather than assuming they exist.

### Fixed

- **Example caller stubs now pass secrets explicitly instead of `secrets:
  inherit`.** GitHub only inherits org/repo secrets into a reusable workflow
  owned by the *same* org/user, so a cross-owner consumer (e.g. a `UCD-SERG`-org
  repo calling these `d-morrison`-user-owned workflows) inherited an empty
  `CLAUDE_CODE_OAUTH_TOKEN` and every `@claude` run failed env-validation
  ("… is required when using direct Anthropic API"). `examples/claude.yml` and
  `examples/claude-code-review.yml` now pass `CLAUDE_CODE_OAUTH_TOKEN` (and the
  optional `SUBMODULES_TOKEN` / `WORKFLOW_TOKEN`) explicitly, which resolves
  caller-side and works regardless of owner. Existing consumers copied from the
  old stubs must make the same change (#49).
- `claude-code-review` now sets `allowed_bots: github-actions[bot]`, so the
  review `claude.yml` re-dispatches after an `@claude` run pushes commits can
  actually run. The action's agent mode (used by `workflow_dispatch`) blocks
  bot actors by default, so dispatched reviews previously failed with "Workflow
  initiated by non-human actor" — and, having entered the per-PR concurrency
  group, canceled the parallel `synchronize` auto-review on their way out,
  leaving the push with no review at all.
- `claude-code-review`'s "collapse previous review comments" step is no longer
  gated to `pull_request`, so a dispatched (`workflow_dispatch`) review that
  wins the per-PR concurrency race also folds earlier pushes' review comments as
  OUTDATED instead of leaving them expanded.

### Security

- **All third-party actions are now pinned to full commit SHAs** (with the
  human-readable version in a trailing comment), following GitHub's
  [recommended hardening posture](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions).
  A SHA is immutable, so a re-pointed tag or a compromised upstream can no longer
  silently change what runs — most important for the `preview-deploy` job, which
  runs in the base-repo context with `contents: write` + `pull-requests: write`.
  Added [`.github/dependabot.yml`](.github/dependabot.yml) (`github-actions`
  ecosystem, weekly, grouped, covering `.github/workflows/` and each composite
  action) so the pins are auto-bumped as upstreams publish releases instead of
  freezing. First-party `d-morrison/gha/*@v1` self-references and the
  `examples/` templates intentionally still track the `@v1` major tag (#48).

## [v1] — initial pilot set

Reusable workflows + composite actions:

- `check-bibliography-dois` — validate book/article BibTeX entries have
  resolvable DOIs matching CrossRef metadata.
- `check-links` — lychee link check with bundled config, PR skip-label, and
  auto-issue on `main`.
- `check-non-standard-chars` — detect curly quotes / en–em dashes in `.qmd`
  and `.R` files.
- `check-news` — enforce a `NEWS.md` changelog entry on PRs (wraps
  `UCD-SERG/changelog-check-action`).
- `summary` — AI summary comment on newly opened issues.

[Unreleased]: https://github.com/d-morrison/gha/compare/v1...main
[v1]: https://github.com/d-morrison/gha/releases/tag/v1
