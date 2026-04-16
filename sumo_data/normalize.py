from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .basho import split_basho_id


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def upsert_matches(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    rows = payload.get("torikumi") or []
    count = 0
    for match in rows:
        basho_id = str(match.get("bashoId") or payload.get("date") or "")
        if not basho_id:
            continue
        year, month = split_basho_id(basho_id)
        conn.execute(
            """
            INSERT INTO raw_matches (
                match_id, basho_id, year, month, day, division, match_no,
                east_id, east_shikona, east_rank, west_id, west_shikona, west_rank,
                winner_id, winner_en, winner_jp, kimarite, source_json, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                winner_id=excluded.winner_id,
                winner_en=excluded.winner_en,
                winner_jp=excluded.winner_jp,
                kimarite=excluded.kimarite,
                source_json=excluded.source_json,
                fetched_at=excluded.fetched_at
            """,
            (
                match.get("id"),
                basho_id,
                year,
                month,
                match.get("day"),
                match.get("division"),
                match.get("matchNo"),
                match.get("eastId"),
                match.get("eastShikona"),
                match.get("eastRank"),
                match.get("westId"),
                match.get("westShikona"),
                match.get("westRank"),
                match.get("winnerId"),
                match.get("winnerEn"),
                match.get("winnerJp"),
                match.get("kimarite"),
                json.dumps(match, ensure_ascii=False, sort_keys=True),
                utc_now(),
            ),
        )
        count += 1
    conn.commit()
    return count


def upsert_banzuke(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    basho_id = str(payload.get("bashoId") or "")
    division = str(payload.get("division") or "")
    if not basho_id or not division:
        return 0

    count = 0
    for side_key in ("east", "west"):
        for entry in payload.get(side_key) or []:
            conn.execute(
                """
                INSERT INTO raw_banzuke (
                    basho_id, division, side, rikishi_id, shikona_en, rank_value,
                    rank, wins, losses, absences, record_json, source_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(basho_id, division, side, rikishi_id) DO UPDATE SET
                    shikona_en=excluded.shikona_en,
                    rank_value=excluded.rank_value,
                    rank=excluded.rank,
                    wins=excluded.wins,
                    losses=excluded.losses,
                    absences=excluded.absences,
                    record_json=excluded.record_json,
                    source_json=excluded.source_json,
                    fetched_at=excluded.fetched_at
                """,
                (
                    basho_id,
                    division,
                    entry.get("side") or side_key.title(),
                    entry.get("rikishiID"),
                    entry.get("shikonaEn"),
                    entry.get("rankValue"),
                    entry.get("rank"),
                    entry.get("wins"),
                    entry.get("losses"),
                    entry.get("absences"),
                    json.dumps(entry.get("record") or [], ensure_ascii=False, sort_keys=True),
                    json.dumps(entry, ensure_ascii=False, sort_keys=True),
                    utc_now(),
                ),
            )
            count += 1
    conn.commit()
    return count


def upsert_wrestler(conn: sqlite3.Connection, payload: dict[str, Any]) -> bool:
    rikishi_id = payload.get("id")
    if rikishi_id is None:
        return False
    conn.execute(
        """
        INSERT INTO raw_wrestlers (
            rikishi_id, sumodb_id, nsk_id, shikona_en, shikona_jp, current_rank,
            heya, birth_date, shusshin, height_cm, weight_kg, debut,
            source_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(rikishi_id) DO UPDATE SET
            sumodb_id=excluded.sumodb_id,
            nsk_id=excluded.nsk_id,
            shikona_en=excluded.shikona_en,
            shikona_jp=excluded.shikona_jp,
            current_rank=excluded.current_rank,
            heya=excluded.heya,
            birth_date=excluded.birth_date,
            shusshin=excluded.shusshin,
            height_cm=excluded.height_cm,
            weight_kg=excluded.weight_kg,
            debut=excluded.debut,
            source_json=excluded.source_json,
            fetched_at=excluded.fetched_at
        """,
        (
            rikishi_id,
            payload.get("sumodbId"),
            payload.get("nskId"),
            payload.get("shikonaEn"),
            payload.get("shikonaJp"),
            payload.get("currentRank"),
            payload.get("heya"),
            payload.get("birthDate"),
            payload.get("shusshin"),
            payload.get("height"),
            payload.get("weight"),
            payload.get("debut"),
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            utc_now(),
        ),
    )
    conn.commit()
    return True


def upsert_kimarite(conn: sqlite3.Connection, payload: dict[str, Any] | list[Any]) -> int:
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    count = 0
    for record in records or []:
        name = record.get("kimarite")
        if not name:
            continue
        conn.execute(
            """
            INSERT INTO raw_kimarite (
                kimarite, usage_count, last_usage, source_json, fetched_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(kimarite) DO UPDATE SET
                usage_count=excluded.usage_count,
                last_usage=excluded.last_usage,
                source_json=excluded.source_json,
                fetched_at=excluded.fetched_at
            """,
            (
                name,
                record.get("count"),
                record.get("lastUsage"),
                json.dumps(record, ensure_ascii=False, sort_keys=True),
                utc_now(),
            ),
        )
        count += 1
    conn.commit()
    return count


def upsert_profile_cache(
    conn: sqlite3.Connection,
    *,
    nsk_id: int,
    profile_url: str,
    cache_path: str,
    status_code: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO raw_profiles (nsk_id, profile_url, cache_path, status_code, fetched_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(nsk_id) DO UPDATE SET
            profile_url=excluded.profile_url,
            cache_path=excluded.cache_path,
            status_code=excluded.status_code,
            fetched_at=excluded.fetched_at
        """,
        (nsk_id, profile_url, cache_path, status_code, utc_now()),
    )
    conn.commit()


def missing_wrestler_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        """
        SELECT id.wrestler_id
        FROM (
            SELECT east_id AS wrestler_id FROM raw_matches WHERE east_id IS NOT NULL
            UNION
            SELECT west_id AS wrestler_id FROM raw_matches WHERE west_id IS NOT NULL
            UNION
            SELECT rikishi_id AS wrestler_id FROM raw_banzuke WHERE rikishi_id IS NOT NULL
        ) id
        LEFT JOIN raw_wrestlers w ON w.rikishi_id = id.wrestler_id
        WHERE w.rikishi_id IS NULL
        ORDER BY id.wrestler_id
        """
    ).fetchall()
    return [int(row["wrestler_id"]) for row in rows]


def rebuild_master_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM matches_master;
        INSERT INTO matches_master (
            match_id, basho_id, year, month, day, division, match_no,
            east_wrestler_id, east_wrestler, east_rank,
            west_wrestler_id, west_wrestler, west_rank,
            winner_id, winner, east_wins, kimarite, fusen_flag
        )
        SELECT
            match_id,
            basho_id,
            year,
            month,
            day,
            division,
            match_no,
            east_id,
            east_shikona,
            east_rank,
            west_id,
            west_shikona,
            west_rank,
            winner_id,
            winner_en,
            CASE
                WHEN winner_id = east_id THEN 1
                WHEN winner_id = west_id THEN 0
                ELSE NULL
            END,
            kimarite,
            CASE WHEN lower(coalesce(kimarite, '')) = 'fusen' THEN 1 ELSE 0 END
        FROM raw_matches;

        DELETE FROM banzuke_master;
        INSERT INTO banzuke_master (
            basho_id, division, side, wrestler_id, shikona_en,
            rank_text, rank_value, wins, losses, absences
        )
        SELECT
            basho_id, division, side, rikishi_id, shikona_en,
            rank, rank_value, wins, losses, absences
        FROM raw_banzuke;

        DELETE FROM wrestlers_master;
        INSERT INTO wrestlers_master (
            wrestler_id, shikona_en, shikona_jp, sumodb_id, nsk_id, current_rank,
            heya, birth_date, shusshin, height_cm, weight_kg, debut, jsa_profile_url
        )
        SELECT
            rikishi_id,
            shikona_en,
            shikona_jp,
            sumodb_id,
            nsk_id,
            current_rank,
            heya,
            birth_date,
            shusshin,
            height_cm,
            weight_kg,
            debut,
            CASE
                WHEN nsk_id IS NOT NULL THEN
                    'https://www.sumo.or.jp/EnSumoDataRikishi/profile/' || nsk_id || '/'
                ELSE NULL
            END
        FROM raw_wrestlers;

        INSERT OR IGNORE INTO wrestlers_master (wrestler_id, shikona_en, current_rank)
        SELECT rikishi_id, shikona_en, rank
        FROM raw_banzuke;
        """
    )
    conn.commit()
