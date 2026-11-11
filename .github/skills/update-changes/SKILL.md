---
name: update-changes
description: Prepare or repair changes.md records when committing changes, writing release notes, or fixing a CI failure caused by missing per-commit change records.
---

# Update changes

## Preparing a commit

1. Read `AGENTS.md`, `changes.md`, `git status --short`, and the staged diff. If nothing is staged, inspect the pending changes without staging unrelated work.
2. Summarize only the verified changes intended for this commit. Do not copy secrets, endpoint URLs, logs, or personal data into the record.
3. Use the user's local date. For a new entry, find the highest number already recorded for that date and add one; if no entry exists for that date, start at `00`. Keep at least two digits (`00`, `01`, ..., `99`, `100`). Add the entry at the top of the records in `changes.md`, after the introduction:

   ```markdown
   ## YYYY-MM-DD - 00 - Short summary

   ### feature

   - Describe the behavior or workflow change.
   ```

4. Classify each item under the applicable heading: `### feature` (new capabilities), `### bug` (verified fixes), `### chore` (CI/build/maintenance), `### docs` (documentation), `### refactor` (behavior-preserving restructuring), or `### test` (tests). Include only categories with content, once each. Do not mark unrelated maintenance as a feature or invent bug fixes.
5. Preserve all earlier entries and their numbering, ordered newest first. When revising the same uncommitted changes, update the pending entry without incrementing its number. On a new date, use that date's `00` if no other entry exists. CI reruns do not add records or increment numbers.
6. Run `python .github/scripts/changes.py latest` and `python -m unittest discover -s .github/scripts -p test_changes.py`.
7. When the user requests a commit, include `changes.md` together with the intended changes. Do not commit or push solely because this skill was invoked.

## Repairing a CI failure

1. Read the commit SHAs reported by the change-record validation job.
2. Inspect each reported commit and prepare accurate notes for its actual changes.
3. CI checks every new non-merge commit, not just the final tree. Adding a separate follow-up commit cannot repair an earlier commit that omitted its record.
4. Ask for explicit permission before amending, rebasing, or force-pushing existing commits. If permission is not granted, explain the blocker without rewriting history.
5. After an authorized repair, run `python .github/scripts/changes.py check --base BASE_SHA --head HEAD_SHA` using the same range as CI, then rerun the focused tests.

## Notification contract

- The first `## ` section is the latest record. The next `## ` starts an older record.
- Every record uses `## YYYY-MM-DD - NN - Summary`, without a `Build` prefix. Dates are newest first; each date's numbers are contiguous from `00`, with the largest number first. Numbering resets on each date, independently of `github.run_number`.
- The latest record must have a non-empty title and at least one supported `### category` heading with non-empty `- ` items. Ungrouped items, unknown categories, duplicate categories, and empty groups fail CI.
- Discord reads only this latest section. CI never calls an AI service or writes commits automatically.
