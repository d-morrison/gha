# Reverse Dependencies (Consumer Repos)

Repos that call `d-morrison/gha` reusable workflows from their
`.github/workflows/`.

> **Note:** This list helps us notify consumers before moving the `@v1` tag in
> a breaking way (or cutting `@v2`). It is **not** authoritative — always
> verify with a code search across the consuming orgs (`d-morrison`,
> `ucdavis`, `UCD-SERG`, `UCLA-PHP`, `UCD-IDDRC`) when releasing a breaking
> change. A GitHub code search for `d-morrison/gha/.github/workflows` across
> those owners is the quickest way to find current callers:
>
> ```bash
> # Requires an authenticated gh (run `gh auth login`, or set GH_TOKEN).
> gh search code 'uses: d-morrison/gha/.github/workflows' --owner d-morrison --owner ucdavis --owner UCD-SERG --owner UCLA-PHP --owner UCD-IDDRC
> ```

## How to register

If your repo calls a `gha` workflow, please open a PR adding it below (or file
an issue asking to be added). Similarly, if you stop using `gha`, open a PR or
issue to be removed.

## Consumer list

| Repo | Workflows used | Notes |
|------|----------------|-------|
| [`Lacaedemon/sparta`](https://github.com/Lacaedemon/sparta) | `check-links`, `claude`, `claude-code-review`, `summary`, `quarto-publish` | Godot game; docs site published via `quarto-publish` (injects recorded gameplay clips through `pre-render-artifact`). |
