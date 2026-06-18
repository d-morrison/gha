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

- `CHANGELOG.md` (this file) — records what changes as the `@v1` tag moves, so
  consumers can see what they picked up.
- `REVDEPS.md` — tracks repos that consume these workflows so breaking changes
  can be announced. See the file for how to register.

### Changed

- Multi-line `run:` blocks in the composite actions and reusable workflows now
  declare `set -euo pipefail` explicitly. GitHub already runs `shell: bash`
  with `-eo pipefail`; the net new protection is `nounset` (unset-variable
  typos now fail fast), plus consistency with the rest of the script logic.

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
