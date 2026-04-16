from __future__ import annotations

import unittest
from pathlib import Path

from sumo_data.fixtures import load_fixture_summaries


class FixtureTests(unittest.TestCase):
    def test_old_data_fixtures_load(self) -> None:
        root = Path(__file__).resolve().parents[1]
        if not (root / "Old Data").exists():
            self.skipTest("Old Data folder is not present")

        summaries = load_fixture_summaries(root)
        by_name = {(summary.path.name, summary.sheet): summary for summary in summaries}

        results = by_name[("haru_2026_makuuchi_all_days_results.xlsx", "Results")]
        self.assertEqual(results.row_count, 298)
        self.assertEqual(results.columns, ["Day", "East wrestler", "West wrestler", "Winner"])

        wrestlers = by_name[("haru_2026_makuuchi_wrestler_attributes.xlsx", "Wrestlers")]
        self.assertEqual(wrestlers.row_count, 42)
        self.assertIn("Wrestler", wrestlers.columns)


if __name__ == "__main__":
    unittest.main()
