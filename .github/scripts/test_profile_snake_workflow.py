from pathlib import Path
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

        self.assertIn("Platane/snk/svg-only@", workflows)
        self.assertIn("schedule:", workflows)
        self.assertIn("workflow_dispatch:", workflows)
        for asset in SNAKE_ASSETS:
            self.assertIn(asset, readme)
            self.assertIn(asset, workflows)
        self.assertNotIn("profile-3d-contrib/profile-grid.svg", readme)


if __name__ == "__main__":
    unittest.main()
