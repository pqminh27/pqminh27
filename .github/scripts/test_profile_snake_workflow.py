from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SNAKE_ASSETS = (
    "profile-assets/github-contribution-grid-snake.svg",
    "profile-assets/github-contribution-grid-snake-dark.svg",
)


class ProfileSnakeWorkflowTest(unittest.TestCase):
    def test_readme_snake_variants_are_generated_by_a_scheduled_workflow(self):
        readme = (ROOT / "README.md").read_text()
        workflows = "\n".join(
            path.read_text()
            for path in (ROOT / ".github/workflows").glob("*.yml")
        )

        self.assertIn(".github/scripts/generate_snake.py", workflows)
        self.assertIn("prepare_snake.py", workflows)
        self.assertIn("schedule:", workflows)
        self.assertIn("workflow_dispatch:", workflows)
        for asset in SNAKE_ASSETS:
            self.assertIn(asset, readme)
            self.assertIn(asset, workflows)
        self.assertNotIn("profile-3d-contrib/profile-grid.svg", readme)

    def test_generated_snake_variants_include_all_seven_rows_in_every_week(self):
        for asset in SNAKE_ASSETS:
            svg = (ROOT / asset).read_text()
            columns = {}
            for column, row in re.findall(r'class="c(\d+)_(\d+)"', svg):
                columns.setdefault(int(column), set()).add(int(row))

            self.assertTrue(columns, f"{asset} has no contribution cells")
            for column, rows in columns.items():
                self.assertEqual(
                    set(range(7)),
                    rows,
                    f"{asset} week {column} is missing rows {sorted(set(range(7)) - rows)}",
                )


if __name__ == "__main__":
    unittest.main()
