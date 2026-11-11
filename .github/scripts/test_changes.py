import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from changes import latest_entry, validate_commits


class LatestEntryTests(unittest.TestCase):
    def test_reads_only_latest_entry_including_subheadings(self):
        text = (
            "# Changes\n\n## 2026-11-11 - 01 - Latest\n\n### feature\n- Current change\n\n### bug\n- Fixed bug\n\n"
            "## 2026-11-11 - 00 - Older\n### docs\n- Old change\n"
        )
        self.assertEqual(
            latest_entry(text),
            "## 2026-11-11 - 01 - Latest\n\n### feature\n- Current change\n\n### bug\n- Fixed bug",
        )

    def test_rejects_missing_or_empty_latest_entry(self):
        for text in ("", "# Changes\n", "## \n- Missing title\n", "## Latest\n\n## Older\n- Old"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                latest_entry(text)

    def test_rejects_unknown_duplicate_empty_or_missing_categories(self):
        for body, error in (
            ("- No category", "Change items must appear under"),
            ("### unknown\n- Change", "Unsupported changes.md category"),
            ("### feature\n- First\n### feature\n- Duplicate", "Duplicate changes.md category"),
            ("### feature\n\n### bug\n- Fix", "must contain a non-empty"),
            ("### bug\n- ", "must contain a non-empty"),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, error):
                latest_entry("## 2026-11-11 - 00 - Latest\n" + body)

    def test_build_numbers_reset_each_day_and_allow_more_than_99(self):
        text = (
            "## 2026-11-12 - 00 - Tomorrow\n### feature\n- New day\n\n"
            "## 2026-11-11 - 01 - Second\n### chore\n- Second change\n\n"
            "## 2026-11-11 - 00 - First\n### chore\n- First change\n"
        )
        self.assertIn("2026-11-12 - 00 - Tomorrow", latest_entry(text))
        many = "\n".join(
            f"## 2026-11-11 - {number:02d} - Change\n### chore\n- Change\n"
            for number in reversed(range(101))
        )
        self.assertTrue(latest_entry(many).startswith("## 2026-11-11 - 100"))

    def test_rejects_gaps_duplicates_invalid_dates_and_wrong_order(self):
        for headers, error in (
            (["2026-11-11 - 01 - Missing zero"], "without gaps or duplicates"),
            (["2026-11-11 - 02 - Gap", "2026-11-11 - 00 - First"], "without gaps or duplicates"),
            (["2026-11-11 - 00 - Duplicate", "2026-11-11 - 00 - First"], "without gaps or duplicates"),
            (["2026-11-12 - 01 - Did not reset", "2026-11-11 - 00 - First"], "without gaps or duplicates"),
            (["2026-11-11 - 00 - Older", "2026-11-12 - 00 - Newer"], "newest date first"),
            (["2026-02-30 - 00 - Invalid date"], "day is out of range"),
            (["2026-11-11 - 0 - Not padded"], "Record headings must use"),
            (["2026-11-11 - 000 - Too padded"], "two digits"),
        ):
            text = "\n".join(f"## {header}\n### chore\n- Change\n" for header in headers)
            with self.subTest(headers=headers), self.assertRaisesRegex(ValueError, error):
                latest_entry(text)


class CommitValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.initial = "# Changes\n\n## 2026-11-10 - 00 - Initial\n### chore\n- Initial change\n"
        self.base = self.commit({"changes.md": self.initial})

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout.strip()

    def commit(self, files):
        for name, content in files.items():
            path = self.repo / name
            if content is None:
                path.unlink()
            else:
                path.write_text(content, encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "-m", "Test change")
        return self.git("rev-parse", "HEAD")

    def test_accepts_initial_and_updated_latest_entries(self):
        self.assertEqual(validate_commits(self.repo, "0" * 40, self.base), 1)
        head = self.commit({
            "changes.md": "# Changes\n\n## 2026-11-11 - 00 - New\n### feature\n- New change\n\n"
            + self.initial.removeprefix("# Changes\n\n")
        })
        self.assertEqual(validate_commits(self.repo, self.base, head), 1)

    def test_rejects_missing_update_even_if_later_commit_has_notes(self):
        missing = self.commit({"code.txt": "New code"})
        head = self.commit({
            "changes.md": "# Changes\n\n## 2026-11-11 - 00 - New\n### feature\n- New code\n\n"
            + self.initial.removeprefix("# Changes\n\n")
        })
        with self.assertRaisesRegex(ValueError, missing[:12] + ": changes.md was not updated"):
            validate_commits(self.repo, self.base, head)

    def test_cli_reads_latest_and_exits_with_error_for_missing_record(self):
        script = str(Path(__file__).with_name("changes.py").resolve())
        latest = subprocess.run(
            [sys.executable, script, "latest"], cwd=self.repo, capture_output=True, text=True
        )
        self.assertEqual(latest.returncode, 0)
        self.assertEqual(latest.stdout.strip(), "## 2026-11-10 - 00 - Initial\n### chore\n- Initial change")
        missing = self.commit({"code.txt": "New code"})
        check = subprocess.run(
            [sys.executable, script, "check", "--base", self.base, "--head", missing],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 1)
        self.assertIn(missing[:12] + ": changes.md was not updated", check.stderr)
        self.assertIn("update-changes skill", check.stderr)

    def test_rejects_edits_to_only_old_entries(self):
        text = (
            "# Changes\n\n## 2026-11-11 - 00 - New\n### feature\n- New change\n\n"
            "## 2026-11-10 - 00 - Old\n### chore\n- Old change\n"
        )
        base = self.commit({"changes.md": text})
        head = self.commit({"changes.md": text.replace("Old change", "Older change")})
        with self.assertRaisesRegex(ValueError, "latest changes.md entry was not updated"):
            validate_commits(self.repo, base, head)

    def test_rejects_deleted_or_empty_change_records(self):
        head = self.commit({"changes.md": None})
        with self.assertRaisesRegex(ValueError, "must not be deleted"):
            validate_commits(self.repo, self.base, head)
        head = self.commit({"changes.md": "## 2026-11-11 - 00 - Empty\n### bug\n"})
        with self.assertRaisesRegex(ValueError, "non-empty"):
            validate_commits(self.repo, self.base, head)

    def test_skips_merge_commit_but_checks_branch_commits(self):
        self.git("checkout", "-b", "feature")
        self.commit({
            "changes.md": "# Changes\n\n## 2026-11-11 - 00 - Feature\n### feature\n- Feature change\n\n"
            + self.initial.removeprefix("# Changes\n\n")
        })
        self.git("checkout", "main")
        main_head = self.commit({
            "changes.md": "# Changes\n\n## 2026-11-11 - 00 - Main\n### chore\n- Main change\n\n"
            + self.initial.removeprefix("# Changes\n\n")
        })
        self.git("merge", "--no-ff", "-s", "ours", "feature", "-m", "Merge feature")
        self.assertEqual(validate_commits(self.repo, self.base, self.git("rev-parse", "HEAD")), 2)
        self.assertEqual(validate_commits(self.repo, main_head, main_head), 0)

    def test_allows_migrating_pre_numbering_records_without_rewriting_history(self):
        legacy = self.commit({"changes.md": "# Changes\n\n## Legacy\n### chore\n- Legacy change\n"})
        head = self.commit({"changes.md": self.initial})
        self.assertEqual(validate_commits(self.repo, legacy, head), 1)


if __name__ == "__main__":
    unittest.main()
