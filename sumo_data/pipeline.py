from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .api import SumoApiClient
from .basho import iter_basho_ids
from .export import export_all
from .fixtures import load_fixture_summaries, write_fixture_summary_csv
from .normalize import (
    missing_wrestler_ids,
    rebuild_master_tables,
    upsert_banzuke,
    upsert_kimarite,
    upsert_matches,
    upsert_profile_cache,
    upsert_wrestler,
)
from .storage import connect, ensure_schema


@dataclass(frozen=True)
class PipelineSummary:
    bashos_attempted: int
    torikumi_rows: int
    banzuke_rows: int
    wrestlers_fetched: int
    jsa_profiles_fetched: int
    exports_dir: Path
    database_path: Path


def run_validation_stage(
    project_root: Path,
    *,
    data_dir: Path,
    start_year: int = 2025,
    end_year: int = 2026,
    division: str = "Makuuchi",
    include_future: bool = False,
    force: bool = False,
    fetch_jsa_profiles: bool = False,
    polite_delay: float = 0.2,
) -> PipelineSummary:
    data_dir = Path(data_dir)
    exports_dir = data_dir / "exports"
    conn = connect(data_dir)
    ensure_schema(conn)

    fixture_summaries = load_fixture_summaries(project_root)
    write_fixture_summary_csv(fixture_summaries, exports_dir / "fixture_summary.csv")

    client = SumoApiClient(data_dir, polite_delay=polite_delay)
    _fetch_kimarite(conn, client, force=force)

    bashos_attempted = 0
    torikumi_rows = 0
    banzuke_rows = 0
    for basho_id in iter_basho_ids(start_year, end_year, include_future=include_future):
        bashos_attempted += 1
        banzuke_rows += _fetch_banzuke(conn, client, basho_id, division, force=force)
        for day in range(1, 16):
            torikumi_rows += _fetch_torikumi(conn, client, basho_id, division, day, force=force)

    wrestlers_fetched = _fetch_missing_wrestlers(conn, client, force=force)
    jsa_profiles_fetched = 0
    if fetch_jsa_profiles:
        jsa_profiles_fetched = _fetch_jsa_profiles(conn, client, force=force)

    rebuild_master_tables(conn)
    export_all(conn, exports_dir, project_root)
    conn.close()

    return PipelineSummary(
        bashos_attempted=bashos_attempted,
        torikumi_rows=torikumi_rows,
        banzuke_rows=banzuke_rows,
        wrestlers_fetched=wrestlers_fetched,
        jsa_profiles_fetched=jsa_profiles_fetched,
        exports_dir=exports_dir,
        database_path=data_dir / "sumo.db",
    )


def validate_existing(project_root: Path, *, data_dir: Path) -> Path:
    conn = connect(data_dir)
    ensure_schema(conn)
    rebuild_master_tables(conn)
    exports_dir = Path(data_dir) / "exports"
    export_all(conn, exports_dir, project_root)
    conn.close()
    return exports_dir


def _fetch_torikumi(conn, client: SumoApiClient, basho_id: str, division: str, day: int, *, force: bool) -> int:
    endpoint = f"/api/basho/{basho_id}/torikumi/{division}/{day}"
    result = client.fetch_json(endpoint, force=force, required=False)
    if result is None:
        return 0
    return upsert_matches(conn, result.payload)


def _fetch_banzuke(conn, client: SumoApiClient, basho_id: str, division: str, *, force: bool) -> int:
    endpoint = f"/api/basho/{basho_id}/banzuke/{division}"
    result = client.fetch_json(endpoint, force=force, required=False)
    if result is None:
        return 0
    return upsert_banzuke(conn, result.payload)


def _fetch_missing_wrestlers(conn, client: SumoApiClient, *, force: bool) -> int:
    count = 0
    for wrestler_id in missing_wrestler_ids(conn):
        result = client.fetch_json(f"/api/rikishi/{wrestler_id}", force=force, required=False)
        if result is None:
            continue
        if upsert_wrestler(conn, result.payload):
            count += 1
    return count


def _fetch_jsa_profiles(conn, client: SumoApiClient, *, force: bool) -> int:
    rows = conn.execute(
        """
        SELECT nsk_id
        FROM raw_wrestlers
        WHERE nsk_id IS NOT NULL
        ORDER BY nsk_id
        """
    ).fetchall()
    count = 0
    for row in rows:
        nsk_id = int(row["nsk_id"])
        body, cache_path, status = client.fetch_jsa_profile(nsk_id, force=force, required=False)
        profile_url = f"https://www.sumo.or.jp/EnSumoDataRikishi/profile/{nsk_id}/"
        if body is not None:
            count += 1
        upsert_profile_cache(
            conn,
            nsk_id=nsk_id,
            profile_url=profile_url,
            cache_path=str(cache_path),
            status_code=status,
        )
    return count


def _fetch_kimarite(conn, client: SumoApiClient, *, force: bool) -> int:
    result = client.fetch_json(
        "/api/kimarite",
        query={"sortField": "kimarite", "sortOrder": "asc", "limit": 500},
        force=force,
        required=False,
    )
    if result is None:
        return 0
    return upsert_kimarite(conn, result.payload)
