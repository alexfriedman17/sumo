from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(data_dir: Path) -> sqlite3.Connection:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(data_dir / "sumo.db")
    conn.row_factory = sqlite3.Row
    # OneDrive-backed workspaces can reject SQLite's sidecar journal writes.
    # Raw JSON remains the audit layer, so the DB can be rebuilt if interrupted.
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS raw_matches (
            match_id TEXT PRIMARY KEY,
            basho_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            division TEXT NOT NULL,
            match_no INTEGER,
            east_id INTEGER,
            east_shikona TEXT,
            east_rank TEXT,
            west_id INTEGER,
            west_shikona TEXT,
            west_rank TEXT,
            winner_id INTEGER,
            winner_en TEXT,
            winner_jp TEXT,
            kimarite TEXT,
            source_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_banzuke (
            basho_id TEXT NOT NULL,
            division TEXT NOT NULL,
            side TEXT NOT NULL,
            rikishi_id INTEGER NOT NULL,
            shikona_en TEXT,
            rank_value INTEGER,
            rank TEXT,
            wins INTEGER,
            losses INTEGER,
            absences INTEGER,
            record_json TEXT,
            source_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (basho_id, division, side, rikishi_id)
        );

        CREATE TABLE IF NOT EXISTS raw_wrestlers (
            rikishi_id INTEGER PRIMARY KEY,
            sumodb_id INTEGER,
            nsk_id INTEGER,
            shikona_en TEXT,
            shikona_jp TEXT,
            current_rank TEXT,
            heya TEXT,
            birth_date TEXT,
            shusshin TEXT,
            height_cm REAL,
            weight_kg REAL,
            debut TEXT,
            source_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_profiles (
            nsk_id INTEGER PRIMARY KEY,
            profile_url TEXT NOT NULL,
            cache_path TEXT,
            status_code INTEGER,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_kimarite (
            kimarite TEXT PRIMARY KEY,
            usage_count INTEGER,
            last_usage TEXT,
            source_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS matches_master (
            match_id TEXT PRIMARY KEY,
            basho_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            division TEXT NOT NULL,
            match_no INTEGER,
            east_wrestler_id INTEGER,
            east_wrestler TEXT,
            east_rank TEXT,
            west_wrestler_id INTEGER,
            west_wrestler TEXT,
            west_rank TEXT,
            winner_id INTEGER,
            winner TEXT,
            east_wins INTEGER,
            kimarite TEXT,
            fusen_flag INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS wrestlers_master (
            wrestler_id INTEGER PRIMARY KEY,
            shikona_en TEXT,
            shikona_jp TEXT,
            sumodb_id INTEGER,
            nsk_id INTEGER,
            current_rank TEXT,
            heya TEXT,
            birth_date TEXT,
            shusshin TEXT,
            height_cm REAL,
            weight_kg REAL,
            debut TEXT,
            jsa_profile_url TEXT
        );

        CREATE TABLE IF NOT EXISTS banzuke_master (
            basho_id TEXT NOT NULL,
            division TEXT NOT NULL,
            side TEXT NOT NULL,
            wrestler_id INTEGER NOT NULL,
            shikona_en TEXT,
            rank_text TEXT,
            rank_value INTEGER,
            wins INTEGER,
            losses INTEGER,
            absences INTEGER,
            PRIMARY KEY (basho_id, division, side, wrestler_id)
        );

        CREATE INDEX IF NOT EXISTS idx_raw_matches_basho_day
            ON raw_matches (basho_id, division, day);
        CREATE INDEX IF NOT EXISTS idx_matches_master_basho_day
            ON matches_master (basho_id, division, day);
        CREATE INDEX IF NOT EXISTS idx_raw_banzuke_basho
            ON raw_banzuke (basho_id, division);
        """
    )
    conn.commit()
