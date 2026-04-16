from __future__ import annotations

import sqlite3
import unittest

from sumo_data.normalize import rebuild_master_tables, upsert_banzuke, upsert_matches, upsert_wrestler
from sumo_data.storage import ensure_schema


class NormalizeTests(unittest.TestCase):
    def test_match_target_and_fusen_flag(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        ensure_schema(conn)
        upsert_matches(
            conn,
            {
                "torikumi": [
                    {
                        "id": "202501-1-1-40-83",
                        "bashoId": "202501",
                        "division": "Makuuchi",
                        "day": 1,
                        "matchNo": 1,
                        "eastId": 40,
                        "eastShikona": "Nishikifuji",
                        "eastRank": "Maegashira 17 East",
                        "westId": 83,
                        "westShikona": "Tokihayate",
                        "westRank": "Maegashira 17 West",
                        "kimarite": "fusen",
                        "winnerId": 83,
                        "winnerEn": "Tokihayate",
                        "winnerJp": "",
                    }
                ]
            },
        )
        upsert_banzuke(
            conn,
            {
                "bashoId": "202501",
                "division": "Makuuchi",
                "east": [
                    {
                        "side": "East",
                        "rikishiID": 40,
                        "shikonaEn": "Nishikifuji",
                        "rankValue": 117,
                        "rank": "Maegashira 17 East",
                        "wins": 0,
                        "losses": 1,
                        "absences": 0,
                        "record": [],
                    }
                ],
                "west": [],
            },
        )
        upsert_wrestler(
            conn,
            {
                "id": 83,
                "sumodbId": 1,
                "nskId": 9999,
                "shikonaEn": "Tokihayate",
                "shikonaJp": "",
                "currentRank": "Maegashira 17 West",
                "height": 180,
                "weight": 150,
            },
        )

        rebuild_master_tables(conn)
        row = conn.execute("SELECT east_wins, fusen_flag FROM matches_master").fetchone()
        self.assertEqual(row["east_wins"], 0)
        self.assertEqual(row["fusen_flag"], 1)

        wrestler = conn.execute(
            "SELECT wrestler_id, jsa_profile_url FROM wrestlers_master WHERE wrestler_id = 83"
        ).fetchone()
        self.assertEqual(wrestler["wrestler_id"], 83)
        self.assertEqual(
            wrestler["jsa_profile_url"],
            "https://www.sumo.or.jp/EnSumoDataRikishi/profile/9999/",
        )


if __name__ == "__main__":
    unittest.main()
