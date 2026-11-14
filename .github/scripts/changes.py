import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


CATEGORIES = {"feature", "bug", "chore", "docs", "refactor", "test"}


def validate_build_numbers(text: str) -> None:
    headers = [line for line in text.splitlines() if line.startswith("## ")]
    if not headers:
        raise ValueError("CHANGELOG.md must contain a latest entry starting with '## '.")
    counts: dict[date, int] = {}
    records: list[tuple[date, int]] = []
    for header in headers:
        match = re.fullmatch(r"## (\d{4}-\d{2}-\d{2}) - (\d{2,})", header)
        if not match:
            raise ValueError("Record headings must use '## YYYY-MM-DD - NN'.")
        day = date.fromisoformat(match[1])
        number = int(match[2])
        if match[2] != f"{number:02d}":
            raise ValueError("Build numbers must use two digits, expanding after 99.")
        if records and day > records[-1][0]:
            raise ValueError("Change records must be ordered newest date first.")
        records.append((day, number))
        counts[day] = counts.get(day, 0) + 1
    for day, number in records:
        counts[day] -= 1
        if number != counts[day]:
            raise ValueError(f"{day}: build numbers must start at 00 and increase without gaps or duplicates.")


def _categorized_entry(text: str, require_description: bool = True) -> str:
    entry: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if entry:
                break
            entry.append(line)
        elif entry:
            entry.append(line)

    if not entry or not entry[0][3:].strip():
        raise ValueError("CHANGELOG.md must contain a latest entry starting with '## '.")
    if require_description:
        first = next((line.strip() for line in entry[1:] if line.strip()), "")
        if not first or first.startswith(("#", "- ")):
            raise ValueError("The latest CHANGELOG.md entry must have a description line right after the heading.")
    category: str | None = None
    has_item = False
    seen: set[str] = set()
    for line in entry[1:]:
        if line.startswith("### "):
            if category and not has_item:
                raise ValueError(f"Category '{category}' must contain a non-empty '- ' item.")
            category = line[4:].strip()
            if category not in CATEGORIES:
                raise ValueError(f"Unsupported CHANGELOG.md category: '{category}'.")
            if category in seen:
                raise ValueError(f"Duplicate CHANGELOG.md category: '{category}'.")
            seen.add(category)
            has_item = False
        elif line.startswith("- ") and line[2:].strip():
            if category is None:
                raise ValueError("Change items must appear under a '### category' heading.")
            has_item = True
    if category is None:
        raise ValueError("The latest CHANGELOG.md entry must contain a '### category' heading.")
    if not has_item:
        raise ValueError(f"Category '{category}' must contain a non-empty '- ' item.")
    return "\n".join(entry).strip()


def latest_entry(text: str) -> str:
    validate_build_numbers(text)
    return _categorized_entry(text)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def validate_commits(repo: Path, base: str, head: str) -> int:
    if not base or set(base) == {"0"}:
        commits = git(repo, "rev-list", "--max-count=1", "--no-merges", head).splitlines()
    else:
        commits = git(repo, "rev-list", "--reverse", "--no-merges", f"{base}..{head}").splitlines()

    errors: list[str] = []
    for commit in commits:
        label = commit[:12]
        changed = git(
            repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--", "CHANGELOG.md"
        ).splitlines()
        if "CHANGELOG.md" not in changed:
            errors.append(f"{label}: CHANGELOG.md was not updated.")
            continue
        if not git(repo, "ls-tree", "--name-only", commit, "--", "CHANGELOG.md").strip():
            errors.append(f"{label}: CHANGELOG.md must not be deleted.")
            continue

        try:
            current = latest_entry(git(repo, "show", f"{commit}:CHANGELOG.md"))
            parents = git(repo, "show", "-s", "--format=%P", commit).split()
            if parents and git(repo, "ls-tree", "--name-only", parents[0], "--", "CHANGELOG.md").strip():
                # Previous commits may predate build numbering.
                previous = _categorized_entry(
                    git(repo, "show", f"{parents[0]}:CHANGELOG.md"), require_description=False
                )
                if current == previous:
                    errors.append(f"{label}: the latest CHANGELOG.md entry was not updated.")
        except ValueError as error:
            errors.append(f"{label}: {error}")

    if errors:
        raise ValueError(
            "\n".join(errors)
            + "\nUse the update-changes skill to prepare the missing records."
            + "\nRepairing existing commits requires explicit permission to rewrite history."
        )
    return len(commits)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read and validate per-commit change records.")
    parser.add_argument("command", choices=["latest", "check"])
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        latest = latest_entry(Path("CHANGELOG.md").read_text(encoding="utf-8"))
        if args.command == "latest":
            print(latest)
        else:
            count = validate_commits(Path.cwd(), args.base, args.head)
            print(f"Validated CHANGELOG.md updates in {count} non-merge commit(s).")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Change record validation failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
