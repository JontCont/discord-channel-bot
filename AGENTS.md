# Commit change records

- Every non-merge commit must update the latest entry in `changes.md`, including documentation-only commits.
- Use the repository `update-changes` skill before preparing a commit.
- Keep entries newest first, using `## YYYY-MM-DD - NN - Summary` without a `Build` prefix.
- Use the user's local date. Number each day's records from `00`, incrementing for new entries and resetting to `00` on the next date. Preserve prior entries and numbering; rerunning CI does not create a record.
- Group items under `### feature`, `### bug`, `### chore`, `### docs`, `### refactor`, or `### test`. Use only relevant categories, without duplicates or empty groups.
- Each category must contain at least one non-empty `- ` item. Classify bug fixes only when the fixed behavior is verified.
- Describe only verified changes. Never include secrets, webhook URLs, or private runtime data.
- Preserve older entries. Updating only an older entry does not satisfy CI.
- Read the latest entry with `python .github/scripts/changes.py latest`.
- Run focused tests with `python -m unittest discover -s .github/scripts -p test_changes.py`.
- Do not amend, rebase, or force-push existing commits without explicit user permission. A follow-up changelog commit does not fix a missing record in an earlier commit.
