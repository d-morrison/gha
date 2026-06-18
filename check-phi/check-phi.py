#!/usr/bin/env python3
"""
Scan a repository (or just a pull request's added lines) for content that looks
like Protected Health Information (PHI) / personally identifiable identifiers.

This is a *heuristic* tripwire, not a HIPAA compliance tool: it flags patterns
that are very unlikely to belong in source control (Social Security numbers,
medical record numbers, dates of birth, PHI column headers in data files) so a
human can review before the data is merged. It is intentionally tuned for high
precision (few false positives) over recall.

Design notes:
- **Values are never printed.** A leaked SSN in a CI log is still a leak, so
  findings report only ``file:line:col`` plus the detector name — never the
  matched text.
- **Diff-scoped by default.** When ``PHI_BASE_REF`` is set (a PR's base SHA),
  only lines *added* by the PR are scanned, so pre-existing fixtures don't
  re-trip the check on every unrelated edit. Otherwise the whole tracked tree
  is scanned (``git ls-files``), which is what runs on ``push``.

Configuration (all via environment variables, set by the composite action):
  PHI_BASE_REF        Git ref/SHA to diff against. Empty => scan whole tree.
  PHI_DETECTORS       Comma list overriding the enabled detector set
                      (choose from: ssn, mrn, dob, csv_phi_header, phone, email).
  PHI_PATHS_IGNORE    Comma/newline-separated glob patterns to skip.
  PHI_ALLOWLIST_FILE  Path to a file of regexes; a match whose text matches any
                      regex is suppressed. Defaults to .github/phi-allowlist.txt
                      when that file exists.
  PHI_FAIL            "true" (default) => exit 1 on findings; otherwise warn
                      (annotations + summary) but exit 0.

Inline suppression: any line containing the token ``phi-allow`` (e.g. a
``# phi-allow`` trailing comment) is skipped entirely.
"""

import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

INLINE_PRAGMA = "phi-allow"
DEFAULT_ALLOWLIST = ".github/phi-allowlist.txt"
DEFAULT_DETECTORS = ("ssn", "mrn", "dob", "csv_phi_header")
CSV_SUFFIXES = (".csv", ".tsv", ".psv")


class Finding(NamedTuple):
    path: str
    line: int
    col: int
    detector: str
    message: str


# ── Individual detectors ────────────────────────────────────────────────────
# Each detector is a callable (path, lineno, line) -> list[(col, message)].
# Detectors must NOT include the matched value in the message.

_SSN_RE = re.compile(r"(?<!\d)(\d{3})-(\d{2})-(\d{4})(?!\d)")


def _valid_ssn(area: str, group: str, serial: str) -> bool:
    """Reject formats the SSA never issues, cutting false positives from
    zip+4, phone fragments, and other dash-grouped numbers."""
    if area in ("000", "666") or area[0] == "9":
        return False
    if group == "00" or serial == "0000":
        return False
    return True


def _detect_ssn(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    out = []
    for m in _SSN_RE.finditer(line):
        if _valid_ssn(m.group(1), m.group(2), m.group(3)):
            out.append((m.start() + 1, "Possible US Social Security Number"))
    return out


_MRN_RE = re.compile(
    r"(?i)\b(?:mrn|medical[\s_-]*record(?:[\s_-]*(?:number|no|num|#))?)\b"
    r"\s*[:#=]?\s*\d{5,12}\b"
)


def _detect_mrn(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    return [
        (m.start() + 1, "Possible Medical Record Number")
        for m in _MRN_RE.finditer(line)
    ]


_DOB_RE = re.compile(
    r"(?i)\b(?:dob|date[\s_-]*of[\s_-]*birth|birth[\s_-]*date)\b"
    r"\s*[:=]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"
)


def _detect_dob(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    return [
        (m.start() + 1, "Possible date of birth")
        for m in _DOB_RE.finditer(line)
    ]


# US phone (off by default — noisy). Requires separators to avoid matching
# arbitrary 10-digit IDs.
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
)


def _detect_phone(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    return [
        (m.start() + 1, "Possible phone number")
        for m in _PHONE_RE.finditer(line)
    ]


# Email (off by default — author/maintainer emails are everywhere in code).
_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _detect_email(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    return [
        (m.start() + 1, "Possible email address")
        for m in _EMAIL_RE.finditer(line)
    ]


# PHI-suggestive column headers in delimited data files. Tokens are normalized
# (lowercased, non-alphanumerics stripped) before comparison.
_PHI_HEADER_TOKENS = {
    "ssn", "socialsecurity", "socialsecuritynumber",
    "mrn", "medicalrecordnumber", "medicalrecordno",
    "patientname", "patientid", "patientfirstname", "patientlastname",
    "dateofbirth", "dob", "birthdate",
    "homeaddress", "streetaddress", "mailingaddress",
    "homephone", "phonenumber", "cellphone",
    "emailaddress",
}


def _detect_csv_phi_header(path: str, lineno: int, line: str) -> List[Tuple[int, str]]:
    if lineno != 1 or not path.lower().endswith(CSV_SUFFIXES):
        return []
    delim = {".tsv": "\t", ".psv": "|"}.get(Path(path).suffix.lower(), ",")
    out = []
    col = 1
    for cell in line.rstrip("\n").split(delim):
        token = re.sub(r"[^a-z0-9]", "", cell.lower())
        if token in _PHI_HEADER_TOKENS:
            out.append((col, "PHI-suggestive column header in data file"))
        col += len(cell) + 1
    return out


DETECTORS: Dict[str, Callable[[str, int, str], List[Tuple[int, str]]]] = {
    "ssn": _detect_ssn,
    "mrn": _detect_mrn,
    "dob": _detect_dob,
    "csv_phi_header": _detect_csv_phi_header,
    "phone": _detect_phone,
    "email": _detect_email,
}


# ── Scope resolution ────────────────────────────────────────────────────────

def _run_git(args: List[str]) -> Optional[str]:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _looks_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def _ignored(rel: str, patterns: List[str]) -> bool:
    return any(
        fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, f"{pat.rstrip('/')}/*")
        for pat in patterns
    )


def _tracked_files() -> List[str]:
    out = _run_git(["ls-files"])
    if out is not None:
        return [p for p in out.splitlines() if p]
    # Fallback: walk the tree, skipping the git dir.
    files = []
    for root, dirs, names in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in names:
            files.append(os.path.relpath(os.path.join(root, n), "."))
    return files


def _scan_lines_all(patterns: List[str]) -> List[Tuple[str, int, str]]:
    """Yield (path, lineno, text) for every line of every tracked text file."""
    rows = []
    for rel in _tracked_files():
        if _ignored(rel, patterns):
            continue
        p = Path(rel)
        if not p.is_file() or _looks_binary(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="strict") as f:
                for lineno, text in enumerate(f, start=1):
                    rows.append((rel, lineno, text))
        except (UnicodeDecodeError, OSError):
            continue  # not text we can scan
    return rows


_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _scan_lines_diff(base_ref: str, patterns: List[str]) -> Optional[List[Tuple[str, int, str]]]:
    """Yield (path, lineno, text) for lines *added* relative to base_ref.
    Returns None if the diff could not be computed (caller falls back to all)."""
    diff = _run_git(["diff", "--unified=0", "--no-color", f"{base_ref}...HEAD"])
    if diff is None:
        return None
    rows: List[Tuple[str, int, str]] = []
    cur_path: Optional[str] = None
    new_lineno = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:]
            cur_path = None if target == "/dev/null" else target[2:]  # strip "b/"
            continue
        if raw.startswith("@@"):
            m = _HUNK_RE.match(raw)
            new_lineno = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            if cur_path is not None and not _ignored(cur_path, patterns):
                rows.append((cur_path, new_lineno, raw[1:] + "\n"))
            new_lineno += 1
    return rows


# ── Allowlisting ────────────────────────────────────────────────────────────

def _load_allowlist(path: str) -> List[re.Pattern]:
    if not path or not os.path.isfile(path):
        return []
    pats = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                pats.append(re.compile(line))
            except re.error as e:
                print(f"::warning::Invalid allowlist regex '{line}': {e}")
    return pats


# ── Main ────────────────────────────────────────────────────────────────────

def _split_list(value: str) -> List[str]:
    return [tok.strip() for tok in re.split(r"[,\n]", value or "") if tok.strip()]


def main() -> int:
    base_ref = os.environ.get("PHI_BASE_REF", "").strip()
    requested = _split_list(os.environ.get("PHI_DETECTORS", ""))
    enabled = requested or list(DEFAULT_DETECTORS)
    unknown = [d for d in enabled if d not in DETECTORS]
    if unknown:
        print(f"::error::Unknown PHI detector(s): {', '.join(unknown)}. "
              f"Valid: {', '.join(DETECTORS)}")
        return 1
    active = [(name, DETECTORS[name]) for name in enabled]

    ignore = _split_list(os.environ.get("PHI_PATHS_IGNORE", ""))
    fail = os.environ.get("PHI_FAIL", "true").strip().lower() != "false"

    allowlist_file = os.environ.get("PHI_ALLOWLIST_FILE", "").strip()
    if not allowlist_file and os.path.isfile(DEFAULT_ALLOWLIST):
        allowlist_file = DEFAULT_ALLOWLIST
    allow = _load_allowlist(allowlist_file)

    if base_ref:
        rows = _scan_lines_diff(base_ref, ignore)
        if rows is None:
            print(f"::warning::Could not diff against '{base_ref}'; "
                  f"scanning the whole tree instead.")
            rows = _scan_lines_all(ignore)
            mode = "whole tree (diff unavailable)"
        else:
            mode = f"lines added since {base_ref[:12]}"
    else:
        rows = _scan_lines_all(ignore)
        mode = "whole tree"

    print(f"Scanning for PHI ({mode}); detectors: {', '.join(enabled)}\n")

    findings: List[Finding] = []
    for path, lineno, text in rows:
        if INLINE_PRAGMA in text.lower():
            continue
        if allow and any(p.search(text) for p in allow):
            continue
        for name, fn in active:
            for col, message in fn(path, lineno, text):
                findings.append(Finding(path, lineno, col, name, message))

    level = "error" if fail else "warning"
    for f in findings:
        # Value deliberately omitted — never echo PHI to the log.
        print(f"::{level} file={f.path},line={f.line},col={f.col}::"
              f"[phi:{f.detector}] {f.message} (value redacted). "
              f"If this is synthetic/non-PHI, add a 'phi-allow' comment on the "
              f"line or an entry in {allowlist_file or DEFAULT_ALLOWLIST}.")

    if not findings:
        print("✓ No PHI-like content detected.")
        return 0

    files = len({f.path for f in findings})
    print(f"\n✗ Found {len(findings)} possible PHI item(s) in {files} file(s). "
          f"Values are redacted above; review the listed file:line locations.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
