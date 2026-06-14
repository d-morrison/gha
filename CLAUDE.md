# CLAUDE.md

Guidance for Claude Code when working in this repository.

## About this repo

Central, reusable GitHub Actions for `d-morrison` / `UCD-SERG` / `ucdavis` R-package
and Quarto repositories (see [`README.md`](README.md)). Each capability ships as a
composite action plus a `workflow_call` reusable workflow. Consumers pin to `@v1`.

## Code review guidelines

When reviewing a pull request (e.g. via `/review`, `/code-review`, or as a Claude
PR bot), evaluate the diff against **both** of the following, in addition to
correctness:

### 1. The SERG lab manual

The [UCD-SERG lab manual](https://ucd-serg.github.io/lab-manual/) is the lab's
authority on coding conventions. Hold changes to its standards, especially:

- [Coding style](https://ucd-serg.github.io/lab-manual/coding-style.html) —
  object naming, line breaks/formatting, function documentation, comments,
  message/communication style, and Quarto code-reference conventions (backticked
  `pkg::fn()`, markdown package links — no raw HTML in `.qmd`).
- [Coding practices](https://ucd-serg.github.io/lab-manual/coding-practices.html) —
  function decomposition and length limits, testing requirements, the QA
  checklist, documentation, `{here}` for paths, and tidyverse idioms.
- [Code repositories](https://ucd-serg.github.io/lab-manual/code-repositories.html) —
  repository organization and version-control practices.

The manual defers to the [tidyverse style guide](https://style.tidyverse.org/)
for R; prefer tidyverse idioms and the native `|>` pipe.

### 2. d-morrison's review priorities

Above all, code should be **highly modular and idiomatic**:

- **Modular / decomposed.** Favor small, single-purpose functions over long
  monolithic blocks. Flag duplicated logic (DRY), functions that do too much,
  deep nesting, and steps that should be extracted and named. In workflows and
  composite actions, factor shared logic into reusable units rather than copying
  it between files.
- **Idiomatic.** Code should read like the surrounding code and like the
  ecosystem's conventions — idiomatic R (tidyverse), idiomatic YAML/GitHub
  Actions, idiomatic shell. Prefer the standard, well-known way over a clever or
  bespoke one. Match existing naming, structure, and formatting in the file.
- Keep these front-of-mind: surface modularity and idiom issues even when the
  code is otherwise correct.

Be specific and cite the relevant manual section or principle when raising a
point. Distinguish blocking issues from optional suggestions.
