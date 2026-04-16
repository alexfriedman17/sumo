from __future__ import annotations

import unittest
from datetime import date

from sumo_data.basho import basho_id, iter_basho_ids, split_basho_id


class BashoTests(unittest.TestCase):
    def test_basho_id(self) -> None:
        self.assertEqual(basho_id(2025, 1), "202501")
        self.assertEqual(split_basho_id("202511"), (2025, 11))

    def test_iter_basho_ids_skips_future_months(self) -> None:
        ids = list(iter_basho_ids(2025, 2026, as_of=date(2026, 4, 16)))
        self.assertEqual(
            ids,
            [
                "202501",
                "202503",
                "202505",
                "202507",
                "202509",
                "202511",
                "202601",
                "202603",
            ],
        )


if __name__ == "__main__":
    unittest.main()
