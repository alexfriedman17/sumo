from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from .fixtures import load_haru_2026_results


def export_all(conn: sqlite3.Connection, exports_dir: Path, project_root: Path) -> None:
    exports_dir.mkdir(parents=True, exist_ok=True)
    for table in ("matches_master", "wrestlers_master", "banzuke_master"):
        export_query(conn, f"SELECT * FROM {table} ORDER BY 1", exports_dir / f"{table}.csv")

    export_query(
        conn,
        """
        SELECT
            basho_id,
            year,
            month,
            division,
            COUNT(*) AS bout_count,
            COUNT(DISTINCT day) AS day_count,
            MIN(day) AS first_day,
            MAX(day) AS last_day,
            SUM(CASE WHEN winner_id IS NULL THEN 1 ELSE 0 END) AS missing_winner_count,
            SUM(CASE WHEN east_wins IS NULL THEN 1 ELSE 0 END) AS missing_target_count,
            SUM(fusen_flag) AS fusen_count,
            SUM(CASE WHEN kimarite IS NULL OR trim(kimarite) = '' THEN 1 ELSE 0 END)
                AS missing_kimarite_count
        FROM matches_master
        GROUP BY basho_id, year, month, division
        ORDER BY basho_id, division
        """,
        exports_dir / "validation_basho_summary.csv",
    )

    export_query(
        conn,
        """
        SELECT
            basho_id,
            year,
            month,
            day,
            division,
            COUNT(*) AS bout_count,
            SUM(CASE WHEN winner_id IS NULL THEN 1 ELSE 0 END) AS missing_winner_count,
            SUM(fusen_flag) AS fusen_count,
            SUM(CASE WHEN kimarite IS NULL OR trim(kimarite) = '' THEN 1 ELSE 0 END)
                AS missing_kimarite_count
        FROM matches_master
        GROUP BY basho_id, year, month, day, division
        ORDER BY basho_id, division, day
        """,
        exports_dir / "validation_bout_counts_by_basho_day.csv",
    )

    export_query(
        conn,
        """
        SELECT basho_id, division, day, match_no, COUNT(*) AS duplicate_count
        FROM matches_master
        GROUP BY basho_id, division, day, match_no
        HAVING COUNT(*) > 1
        ORDER BY basho_id, division, day, match_no
        """,
        exports_dir / "validation_duplicates.csv",
    )

    export_query(
        conn,
        """
        WITH match_wrestlers AS (
            SELECT basho_id, division, day, match_id, 'East' AS side,
                   east_wrestler_id AS wrestler_id, east_wrestler AS shikona
            FROM matches_master
            UNION ALL
            SELECT basho_id, division, day, match_id, 'West' AS side,
                   west_wrestler_id AS wrestler_id, west_wrestler AS shikona
            FROM matches_master
        )
        SELECT mw.*
        FROM match_wrestlers mw
        LEFT JOIN wrestlers_master wm ON wm.wrestler_id = mw.wrestler_id
        WHERE mw.wrestler_id IS NOT NULL AND wm.wrestler_id IS NULL
        ORDER BY basho_id, day, match_id, side
        """,
        exports_dir / "validation_unknown_wrestlers.csv",
    )

    export_query(
        conn,
        """
        WITH bashos AS (
            SELECT DISTINCT basho_id, division FROM matches_master
            UNION
            SELECT DISTINCT basho_id, division FROM banzuke_master
        ),
        match_ids AS (
            SELECT basho_id, division, east_wrestler_id AS wrestler_id FROM matches_master
            UNION
            SELECT basho_id, division, west_wrestler_id AS wrestler_id FROM matches_master
        ),
        banzuke_counts AS (
            SELECT basho_id, division, COUNT(DISTINCT wrestler_id) AS banzuke_wrestler_count
            FROM banzuke_master
            GROUP BY basho_id, division
        ),
        match_counts AS (
            SELECT basho_id, division, COUNT(DISTINCT wrestler_id) AS match_wrestler_count
            FROM match_ids
            GROUP BY basho_id, division
        ),
        missing_counts AS (
            SELECT
                mi.basho_id,
                mi.division,
                COUNT(DISTINCT mi.wrestler_id) AS match_wrestlers_missing_from_banzuke
            FROM match_ids mi
            LEFT JOIN banzuke_master bm
                ON bm.basho_id = mi.basho_id
                AND bm.division = mi.division
                AND bm.wrestler_id = mi.wrestler_id
            WHERE mi.wrestler_id IS NOT NULL AND bm.wrestler_id IS NULL
            GROUP BY mi.basho_id, mi.division
        )
        SELECT
            b.basho_id,
            b.division,
            COALESCE(bc.banzuke_wrestler_count, 0) AS banzuke_wrestler_count,
            COALESCE(mc.match_wrestler_count, 0) AS match_wrestler_count,
            COALESCE(mis.match_wrestlers_missing_from_banzuke, 0)
                AS match_wrestlers_missing_from_banzuke
        FROM bashos b
        LEFT JOIN banzuke_counts bc
            ON bc.basho_id = b.basho_id AND bc.division = b.division
        LEFT JOIN match_counts mc
            ON mc.basho_id = b.basho_id AND mc.division = b.division
        LEFT JOIN missing_counts mis
            ON mis.basho_id = b.basho_id AND mis.division = b.division
        ORDER BY b.basho_id, b.division
        """,
        exports_dir / "validation_banzuke_coverage.csv",
    )

    export_query(
        conn,
        """
        WITH match_wrestlers AS (
            SELECT basho_id, division, day, match_id, 'East' AS side,
                   east_wrestler_id AS wrestler_id, east_wrestler AS shikona,
                   east_rank AS rank_text
            FROM matches_master
            UNION ALL
            SELECT basho_id, division, day, match_id, 'West' AS side,
                   west_wrestler_id AS wrestler_id, west_wrestler AS shikona,
                   west_rank AS rank_text
            FROM matches_master
        )
        SELECT DISTINCT mw.*
        FROM match_wrestlers mw
        LEFT JOIN banzuke_master bm
            ON bm.basho_id = mw.basho_id
            AND bm.division = mw.division
            AND bm.wrestler_id = mw.wrestler_id
        WHERE mw.wrestler_id IS NOT NULL AND bm.wrestler_id IS NULL
        ORDER BY mw.basho_id, mw.day, mw.match_id, mw.side
        """,
        exports_dir / "validation_match_wrestlers_missing_from_banzuke.csv",
    )

    export_fixture_overlap(conn, exports_dir / "validation_fixture_overlap_haru_2026.csv", project_root)
    write_markdown_report(conn, exports_dir / "validation_report.md")


def export_query(conn: sqlite3.Connection, query: str, out_path: Path) -> None:
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    fieldnames = [description[0] for description in cursor.description or []]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def export_fixture_overlap(conn: sqlite3.Connection, out_path: Path, project_root: Path) -> None:
    fixture_rows = load_haru_2026_results(project_root)
    api_rows = conn.execute(
        """
        SELECT day, east_wrestler, west_wrestler, winner
        FROM matches_master
        WHERE basho_id = '202603' AND division = 'Makuuchi'
        """
    ).fetchall()
    api_by_key = {
        (
            int(row["day"]),
            _norm(row["east_wrestler"]),
            _norm(row["west_wrestler"]),
        ): dict(row)
        for row in api_rows
    }
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "day",
            "old_east",
            "old_west",
            "old_winner",
            "api_winner",
            "found_same_pair",
            "winner_matches",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for old in fixture_rows:
            day = int(old.get("Day") or 0)
            key = (day, _norm(old.get("East wrestler")), _norm(old.get("West wrestler")))
            api = api_by_key.get(key)
            old_winner = _norm(old.get("Winner"))
            api_winner = _norm(api.get("winner")) if api else ""
            writer.writerow(
                {
                    "day": day,
                    "old_east": old.get("East wrestler"),
                    "old_west": old.get("West wrestler"),
                    "old_winner": old.get("Winner"),
                    "api_winner": api.get("winner") if api else "",
                    "found_same_pair": 1 if api else 0,
                    "winner_matches": 1 if api and old_winner == api_winner else 0,
                }
            )


def write_markdown_report(conn: sqlite3.Connection, out_path: Path) -> None:
    totals = conn.execute(
        """
        SELECT
            COUNT(*) AS matches,
            COUNT(DISTINCT basho_id) AS bashos,
            MIN(basho_id) AS first_basho,
            MAX(basho_id) AS last_basho,
            SUM(CASE WHEN winner_id IS NULL THEN 1 ELSE 0 END) AS missing_winners,
            SUM(CASE WHEN east_wins IS NULL THEN 1 ELSE 0 END) AS missing_targets,
            SUM(fusen_flag) AS fusen_matches,
            SUM(CASE WHEN kimarite IS NULL OR trim(kimarite) = '' THEN 1 ELSE 0 END)
                AS missing_kimarite
        FROM matches_master
        """
    ).fetchone()
    wrestlers = conn.execute("SELECT COUNT(*) AS count FROM wrestlers_master").fetchone()
    banzuke = conn.execute("SELECT COUNT(*) AS count FROM banzuke_master").fetchone()
    unknowns = conn.execute(
        """
        WITH match_wrestlers AS (
            SELECT east_wrestler_id AS wrestler_id FROM matches_master
            UNION
            SELECT west_wrestler_id AS wrestler_id FROM matches_master
        )
        SELECT COUNT(*) AS count
        FROM match_wrestlers mw
        LEFT JOIN wrestlers_master wm ON wm.wrestler_id = mw.wrestler_id
        WHERE mw.wrestler_id IS NOT NULL AND wm.wrestler_id IS NULL
        """
    ).fetchone()
    banzuke_missing = conn.execute(
        """
        WITH match_ids AS (
            SELECT basho_id, division, east_wrestler_id AS wrestler_id FROM matches_master
            UNION
            SELECT basho_id, division, west_wrestler_id AS wrestler_id FROM matches_master
        )
        SELECT COUNT(*) AS count
        FROM match_ids mi
        LEFT JOIN banzuke_master bm
            ON bm.basho_id = mi.basho_id
            AND bm.division = mi.division
            AND bm.wrestler_id = mi.wrestler_id
        WHERE mi.wrestler_id IS NOT NULL AND bm.wrestler_id IS NULL
        """
    ).fetchone()

    lines = [
        "# Validation Report",
        "",
        "## Loaded Data",
        "",
        f"- Bashos: {totals['bashos'] or 0}",
        f"- Match rows: {totals['matches'] or 0}",
        f"- First basho: {totals['first_basho'] or ''}",
        f"- Last basho: {totals['last_basho'] or ''}",
        f"- Wrestlers: {wrestlers['count'] or 0}",
        f"- Banzuke rows: {banzuke['count'] or 0}",
        "",
        "## Validation Signals",
        "",
        f"- Missing winners: {totals['missing_winners'] or 0}",
        f"- Missing `east_wins` targets: {totals['missing_targets'] or 0}",
        f"- Fusen matches: {totals['fusen_matches'] or 0}",
        f"- Missing kimarite: {totals['missing_kimarite'] or 0}",
        f"- Unknown wrestler IDs after profile fetch: {unknowns['count'] or 0}",
        f"- Match wrestler-basho IDs outside same-division banzuke: {banzuke_missing['count'] or 0}",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()
