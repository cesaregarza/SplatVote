#!/usr/bin/env python3
"""Generate real tournament tier poll YAML files for SplatVote.

Writes `data/categories/tournament_tier_poll_sendou_<id>.yaml` category files
that ask the community to classify a tournament as Major vs Supermajor.

Data sources:
- Tournaments / teams / matches / participants from the SplatTop rankings DB
  (schema `comp_rankings` by default).
- "Ripple score" from the latest `player_rankings.score` snapshot; top
  participants are selected from actual match participants
  (`player_appearance_teams`) by this score.

Design goal: do batch DB reads and write many YAMLs in one run.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

_DEFAULT_SCHEMA = "comp_rankings"
_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_env_file(path: Path) -> None:
    """Minimal .env loader (no external deps)."""
    if not path.exists():
        raise SystemExit(f"Env file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_schema() -> str:
    candidate = os.getenv("RANKINGS_DB_SCHEMA", _DEFAULT_SCHEMA)
    if _SCHEMA_RE.match(candidate):
        return candidate
    print(
        f"Warning: Invalid RANKINGS_DB_SCHEMA '{candidate}', using {_DEFAULT_SCHEMA}",
        file=sys.stderr,
    )
    return _DEFAULT_SCHEMA


def _collect_credentials(prefix: str) -> dict[str, str] | None:
    host = os.getenv(f"{prefix}HOST")
    user = os.getenv(f"{prefix}USER")
    password = os.getenv(f"{prefix}PASSWORD")
    name = os.getenv(f"{prefix}NAME")
    port = os.getenv(f"{prefix}PORT") or "5432"
    sslmode = os.getenv(f"{prefix}SSLMODE") or ""

    if not any([host, user, password, name]):
        return None

    missing = [
        k
        for k, v in [
            ("HOST", host),
            ("USER", user),
            ("PASSWORD", password),
            ("NAME", name),
        ]
        if not v
    ]
    if missing:
        joined = ", ".join(f"{prefix}{k}" for k in missing)
        raise SystemExit(f"Missing required env vars: {joined}")

    return {
        "host": host or "",
        "user": user or "",
        "password": password or "",
        "name": name or "",
        "port": port,
        "sslmode": sslmode,
    }


def build_psql_conn_args() -> tuple[str, Mapping[str, str]]:
    """Return (psql_conn_string, extra_env)."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url, {}

    creds = _collect_credentials("RANKINGS_DB_") or _collect_credentials("DB_")
    if not creds:
        raise SystemExit(
            "Missing database configuration: set DATABASE_URL or RANKINGS_DB_* env vars"
        )

    # Prefer passing password via env (avoid printing secrets).
    env = {"PGPASSWORD": creds["password"]}
    sslmode = f" sslmode={creds['sslmode']}" if creds.get("sslmode") else ""
    conn = (
        f"host={creds['host']} port={creds['port']} dbname={creds['name']} "
        f"user={creds['user']}{sslmode}"
    )
    return conn, env


def run_psql(
    conn: str,
    sql: str,
    *,
    extra_env: Mapping[str, str],
) -> list[list[str]]:
    cmd = [
        "psql",
        conn,
        "-F",
        "\t",
        "-A",
        "-t",
        "-c",
        sql,
    ]
    env = os.environ.copy()
    env.update(extra_env)

    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"psql failed: {proc.returncode}")

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    reader = csv.reader(lines, delimiter="\t")
    return [list(row) for row in reader]


def safe_filename(prefix: str, tournament_id: int) -> str:
    return f"{prefix}_sendou_{int(tournament_id)}.yaml"


def write_yaml(path: Path, data: Mapping[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def select_tournaments(
    conn: str,
    *,
    extra_env: Mapping[str, str],
    schema: str,
    since_days: int,
    size_limit: int,
    prestige_limit: int,
    max_series_events: int,
    max_polls: int | None,
) -> list[dict[str, Any]]:
    since_ms = int((time.time() - since_days * 86400) * 1000)
    poll_limit = int(max_polls) if max_polls and max_polls > 0 else 1_000_000

    # Series heuristic: normalize recurring events down to a "series key".
    #
    # Goals:
    # - Group different casings ("Fry Basket" vs "fry basket")
    # - Group editions with "#<n>" suffixes
    # - Group trailing numeric editions, including ones with parenthetical
    #   descriptors (e.g. "... 30 (Grand Stage)")
    # - Group LUTI-style division splits ("... - Division X")
    # - Group co-host variants ("... + h20")
    #
    # Uses POSIX classes to avoid backslash escaping headaches in SQL.
    series_key_sql = """
COALESCE(
  NULLIF(
    TRIM(
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(
	              regexp_replace(
	                regexp_replace(
	                  regexp_replace(
	                    regexp_replace(lower(name),
	                      '[[:space:]]*[+][[:space:]]*.*$', ''
	                    ),
	                    'season[[:space:]]+[0-9]+',
	                    'season'
	                  ),
	                  '[[:space:]]*[(][^)]*[)][[:space:]]*$', ''
	                ),
                '[[:space:]]*[-][[:space:]]*division[[:space:]].*$', ''
              ),
              '[[:space:]]*#[[:space:]]*[0-9]+.*$', ''
            ),
            '[[:space:]]+[0-9]+[[:space:]]*:[[:space:]]*.*$', ''
          ),
          '[[:space:]]+[0-9]+[^[:alnum:]]*[[:space:]]*$', ''
        ),
        '[^[:alnum:]]+[[:space:]]*$', ''
      )
    ),
    ''
  ),
  '(unknown)'
)
""".strip()

    sql = f"""
WITH latest AS (
  SELECT MAX(calculated_at_ms)::bigint AS ts
  FROM "{schema}".player_rankings
),
t AS (
  SELECT
    tournament_id::bigint AS tournament_id,
    name::text AS name,
    CASE
      WHEN start_time_ms < 1000000000000 THEN start_time_ms * 1000
      ELSE start_time_ms
    END::bigint AS start_ms,
    team_count::int AS team_count,
    participated_users_count::int AS users,
    match_count::int AS match_count
  FROM "{schema}".tournaments
  WHERE is_finalized IS TRUE
    AND is_ranked IS TRUE
),
eligible_raw AS (
  SELECT *
  FROM t
  WHERE start_ms >= {since_ms}
    AND team_count > 0
    AND users > 0
    AND match_count > 0
),
eligible AS (
  SELECT
    *,
    {series_key_sql}::text AS series_key
  FROM eligible_raw
),
series_ranked AS (
  SELECT
    e.*,
    COUNT(*) OVER (PARTITION BY e.series_key)::int AS series_event_count,
    ROW_NUMBER() OVER (
      PARTITION BY e.series_key
      ORDER BY e.start_ms DESC, e.tournament_id DESC
    ) AS series_rn
  FROM eligible e
),
series_latest AS (
  SELECT *
  FROM series_ranked
  WHERE series_rn = 1
    AND series_event_count <= {int(max_series_events)}
),
ranked_ord AS (
  SELECT
    player_id::bigint AS player_id,
    ROW_NUMBER() OVER (ORDER BY score DESC) AS ord_rank
  FROM "{schema}".player_rankings
  WHERE calculated_at_ms = (SELECT ts FROM latest)
),
participants AS (
  SELECT DISTINCT pat.tournament_id::bigint AS tournament_id,
                  pat.player_id::bigint AS player_id
  FROM "{schema}".player_appearance_teams pat
  JOIN series_latest e ON e.tournament_id = pat.tournament_id
),
strength AS (
  SELECT
    p.tournament_id,
    COUNT(*)::int AS participant_count,
    COUNT(*) FILTER (WHERE ro.ord_rank <= 100)::int AS top100_count,
    (COUNT(*) FILTER (WHERE ro.ord_rank <= 100)::double precision
      / NULLIF(COUNT(*)::double precision, 0)) AS top100_share
  FROM participants p
  LEFT JOIN ranked_ord ro ON ro.player_id = p.player_id
  GROUP BY p.tournament_id
),
size_pick AS (
  SELECT tournament_id FROM (
    (SELECT tournament_id FROM series_latest ORDER BY team_count DESC, users DESC LIMIT {size_limit})
    UNION
    (SELECT tournament_id FROM series_latest ORDER BY users DESC, team_count DESC LIMIT {size_limit})
    UNION
    (SELECT tournament_id FROM series_latest ORDER BY match_count DESC, team_count DESC LIMIT {size_limit})
  ) x
),
	prestige_pick AS (
	  SELECT tournament_id
	  FROM strength
	  ORDER BY top100_share DESC NULLS LAST, top100_count DESC, participant_count DESC
	  LIMIT {prestige_limit}
	),
	picked AS (
	  SELECT tournament_id FROM size_pick
	  UNION
	  SELECT tournament_id FROM prestige_pick
	),
	ranks AS (
	  SELECT
	    e.tournament_id::bigint AS tournament_id,
	    ROW_NUMBER() OVER (
	      ORDER BY e.team_count DESC, e.users DESC, e.start_ms DESC
	    ) AS team_rn,
	    ROW_NUMBER() OVER (
	      ORDER BY e.users DESC, e.team_count DESC, e.start_ms DESC
	    ) AS users_rn,
	    ROW_NUMBER() OVER (
	      ORDER BY e.match_count DESC, e.team_count DESC, e.start_ms DESC
	    ) AS match_rn,
	    ROW_NUMBER() OVER (
	      ORDER BY s.top100_share DESC NULLS LAST,
	               s.top100_count DESC,
	               s.participant_count DESC
	    ) AS prestige_rn
	  FROM series_latest e
	  LEFT JOIN strength s ON s.tournament_id = e.tournament_id
	),
	final AS (
	  SELECT
	    e.tournament_id,
	    e.name,
	    e.series_key,
	    e.series_event_count,
	    e.start_ms,
	    r.team_rn,
	    r.users_rn,
	    r.match_rn,
	    r.prestige_rn
	  FROM series_latest e
	  JOIN picked p ON p.tournament_id = e.tournament_id
	  JOIN ranks r ON r.tournament_id = e.tournament_id
	  ORDER BY
	    LEAST(r.team_rn, r.users_rn, r.match_rn, r.prestige_rn) ASC,
	    e.start_ms DESC,
	    e.tournament_id DESC
	  LIMIT {poll_limit}
	)
	SELECT
	  tournament_id::text,
	  name::text,
	  series_key::text,
	  series_event_count::text
	FROM final
	ORDER BY start_ms DESC, tournament_id DESC;
	"""

    rows = run_psql(conn, sql, extra_env=extra_env)
    return [
        {
            "tournament_id": int(tid),
            "name": name,
            "series_key": series_key,
            "series_event_count": int(series_event_count)
            if str(series_event_count).strip()
            else None,
        }
        for tid, name, series_key, series_event_count in rows
    ]


def fetch_top_participants(
    conn: str,
    *,
    extra_env: Mapping[str, str],
    schema: str,
    tournament_ids: Sequence[int],
    limit: int,
) -> dict[int, list[str]]:
    if not tournament_ids:
        return {}

    ids_sql = ",".join(str(int(t)) for t in tournament_ids)
    sql = f"""
WITH latest AS (
  SELECT MAX(calculated_at_ms)::bigint AS ts
  FROM "{schema}".player_rankings
),
participants AS (
  SELECT DISTINCT tournament_id::bigint AS tournament_id,
                  player_id::bigint AS player_id
  FROM "{schema}".player_appearance_teams
  WHERE tournament_id = ANY(string_to_array('{ids_sql}', ',')::bigint[])
),
scored AS (
  SELECT
    p.tournament_id,
    COALESCE(pl.display_name, '(unknown)')::text AS display_name,
    pr.score::double precision AS score,
    ROW_NUMBER() OVER (
      PARTITION BY p.tournament_id
      ORDER BY pr.score DESC NULLS LAST, pl.display_name ASC, p.player_id ASC
    ) AS rn
  FROM participants p
  LEFT JOIN "{schema}".players pl ON pl.player_id = p.player_id
  LEFT JOIN "{schema}".player_rankings pr
    ON pr.player_id = p.player_id
   AND pr.calculated_at_ms = (SELECT ts FROM latest)
)
SELECT tournament_id::text, display_name
FROM scored
WHERE rn <= {int(limit)}
ORDER BY tournament_id::bigint, rn::int;
"""

    rows = run_psql(conn, sql, extra_env=extra_env)
    out: dict[int, list[str]] = {}
    for tid_str, display_name in rows:
        out.setdefault(int(tid_str), []).append(display_name)
    return out


def fetch_winner_teams(
    conn: str,
    *,
    extra_env: Mapping[str, str],
    schema: str,
    tournament_ids: Sequence[int],
    limit: int,
) -> dict[int, list[str]]:
    if not tournament_ids:
        return {}

    ids_sql = ",".join(str(int(t)) for t in tournament_ids)
    sql = f"""
WITH matches_clean AS (
  SELECT
    tournament_id::bigint AS tournament_id,
    winner_team_id::bigint AS winner_team_id,
    loser_team_id::bigint  AS loser_team_id
  FROM "{schema}".matches
  WHERE tournament_id = ANY(string_to_array('{ids_sql}', ',')::bigint[])
    AND COALESCE(is_bye, FALSE) IS FALSE
),
wins AS (
  SELECT tournament_id, winner_team_id AS team_id, COUNT(*)::int AS wins
  FROM matches_clean
  WHERE winner_team_id IS NOT NULL
  GROUP BY tournament_id, team_id
),
losses AS (
  SELECT tournament_id, loser_team_id AS team_id, COUNT(*)::int AS losses
  FROM matches_clean
  WHERE loser_team_id IS NOT NULL
  GROUP BY tournament_id, team_id
),
team_stats AS (
  SELECT
    tt.tournament_id::bigint AS tournament_id,
    tt.team_id::bigint AS team_id,
    COALESCE(tt.name, '(unknown)')::text AS team_name,
    COALESCE(w.wins, 0)::int AS wins,
    COALESCE(l.losses, 0)::int AS losses,
    ROW_NUMBER() OVER (
      PARTITION BY tt.tournament_id
      ORDER BY COALESCE(w.wins, 0) DESC, COALESCE(l.losses, 0) ASC, tt.name ASC
    ) AS rn
  FROM "{schema}".tournament_teams tt
  LEFT JOIN wins w
    ON w.tournament_id = tt.tournament_id AND w.team_id = tt.team_id
  LEFT JOIN losses l
    ON l.tournament_id = tt.tournament_id AND l.team_id = tt.team_id
  WHERE tt.tournament_id = ANY(string_to_array('{ids_sql}', ',')::bigint[])
)
SELECT tournament_id::text, team_name
FROM team_stats
WHERE rn <= {int(limit)}
ORDER BY tournament_id::bigint, rn::int;
"""

    rows = run_psql(conn, sql, extra_env=extra_env)
    out: dict[int, list[str]] = {}
    for tid_str, team_name in rows:
        out.setdefault(int(tid_str), []).append(team_name)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate tournament tier poll YAMLs")
    ap.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional .env file to load (e.g. /root/dev/SplatTop/.env)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/categories"),
        help="Output directory for category YAML files (default: data/categories)",
    )
    ap.add_argument(
        "--since-days",
        type=int,
        default=365,
        help="Only consider tournaments in the last N days (default: 365)",
    )
    ap.add_argument(
        "--max-series-events",
        type=int,
        default=30,
        help=(
            "Ignore series with more than this many events in the window "
            "(default: 30)"
        ),
    )
    ap.add_argument(
        "--max-polls",
        type=int,
        default=None,
        help=(
            "Hard cap on number of tournaments/polls to generate "
            "(default: no cap)"
        ),
    )
    ap.add_argument(
        "--size-limit",
        type=int,
        default=20,
        help="Per-metric size pick count (default: 20)",
    )
    ap.add_argument(
        "--prestige-limit",
        type=int,
        default=30,
        help="Elite-density pick count (default: 30)",
    )
    ap.add_argument(
        "--top-participants",
        type=int,
        default=10,
        help="Top participant list size (default: 10)",
    )
    ap.add_argument(
        "--winner-teams",
        type=int,
        default=4,
        help="Winner team list size (default: 4)",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing tournament poll YAML files",
    )
    ap.add_argument(
        "--deactivate-unselected",
        action="store_true",
        help=(
            "Set is_active=false for existing tournament_tier_poll_sendou_*.yaml "
            "files not selected by this run"
        ),
    )
    args = ap.parse_args()

    if args.env_file:
        load_env_file(args.env_file)

    schema = resolve_schema()
    conn, extra_env = build_psql_conn_args()

    tournaments = select_tournaments(
        conn,
        extra_env=extra_env,
        schema=schema,
        since_days=int(args.since_days),
        size_limit=int(args.size_limit),
        prestige_limit=int(args.prestige_limit),
        max_series_events=int(args.max_series_events),
        max_polls=int(args.max_polls) if args.max_polls is not None else None,
    )

    tournament_ids = [int(t["tournament_id"]) for t in tournaments]
    top_participants = fetch_top_participants(
        conn,
        extra_env=extra_env,
        schema=schema,
        tournament_ids=tournament_ids,
        limit=int(args.top_participants),
    )
    winner_teams = fetch_winner_teams(
        conn,
        extra_env=extra_env,
        schema=schema,
        tournament_ids=tournament_ids,
        limit=int(args.winner_teams),
    )

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_ids = {int(t["tournament_id"]) for t in tournaments}
    if args.deactivate_unselected:
        for existing in out_dir.glob("tournament_tier_poll_sendou_*.yaml"):
            match = re.search(r"_sendou_(\d+)\.yaml$", existing.name)
            if not match:
                continue
            tid = int(match.group(1))
            if tid in selected_ids:
                continue
            try:
                data = yaml.safe_load(existing.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            if isinstance(data, dict) and data.get("is_active") is True:
                data["is_active"] = False
                write_yaml(existing, data)

    written = 0
    skipped = 0
    for t in tournaments:
        tid = int(t["tournament_id"])
        name = str(t["name"])

        file_path = out_dir / safe_filename("tournament_tier_poll", tid)
        if file_path.exists() and not args.overwrite:
            skipped += 1
            continue

        category = {
            "name": f"Tournament tier: {name}",
            "description": f"Which tier best fits {name}?",
            "comparison_mode": "single_choice",
            "is_active": True,
            "item_group": "Tournament Tiers",
            "settings": {
                "private_results": True,
                "allow_comments": False,
                "tournament": {
                    "name": name,
                    "id": f"sendou-{tid}",
                    "url": f"https://sendou.ink/to/{tid}/brackets",
                    "top_participants": [
                        {"name": p} for p in top_participants.get(tid, [])
                    ],
                    "winners": [{"name": w} for w in winner_teams.get(tid, [])],
                },
            },
        }

        write_yaml(file_path, category)
        written += 1

    print(
        f"Generated {written} poll YAMLs in {out_dir} (skipped {skipped}).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
