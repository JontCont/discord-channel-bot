---
name: update-changes
description: Prepare or repair changes.md records when committing changes, writing release notes, or fixing a CI failure caused by missing per-commit change records.
---

# Update changes

## Preparing a commit

1. Read `AGENTS.md`, `changes.md`, `git status --short`, and the staged diff. If nothing is staged, inspect the pending changes without staging unrelated work.
2. Summarize only the verified changes intended for this commit. Do not copy secrets, endpoint URLs, logs, or personal data into the record.
3. Add a new entry at the top of the records in `changes.md`, after the file introduction:

   ```markdown
   ## YYYY-MM-DD - Short summary

   ### feature

   - Describe the behavior or workflow change.
   ```

4. Classify each item under the applicable heading: `### feature` (new capabilities), `### bug` (verified fixes), `### chore` (CI/build/maintenance), `### docs` (documentation), `### refactor` (behavior-preserving restructuring), or `### test` (tests). Include only categories with content, once each. Do not mark unrelated maintenance as a feature or invent bug fixes.
5. Preserve all earlier entries. When revising the same uncommitted changes, update the pending entry instead of adding duplicate entries.
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
- The latest record must have a non-empty title and at least one supported `### category` heading with non-empty `- ` items. Ungrouped items, unknown categories, duplicate categories, and empty groups fail CI.
- Discord reads only this latest section. CI never calls an AI service or writes commits automatically.
