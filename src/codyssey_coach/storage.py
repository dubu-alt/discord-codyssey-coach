from __future__ import annotations

import sqlite3
from pathlib import Path

from .missions import COURSE_END, COURSE_START, MISSIONS, get_mission
from .planner import MissionProgress, apply_evaluation


class CoachStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    discord_user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    course_start TEXT NOT NULL,
                    course_end TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS mission_progress (
                    discord_user_id TEXT NOT NULL,
                    mission_id TEXT NOT NULL,
                    pass_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (discord_user_id, mission_id)
                );

                CREATE TABLE IF NOT EXISTS weekly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id TEXT NOT NULL,
                    completed TEXT NOT NULL,
                    study_hours INTEGER NOT NULL,
                    blockers TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def ensure_user(self, discord_user_id: str, display_name: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO users (discord_user_id, display_name, course_start, course_end)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET display_name = excluded.display_name
                """,
                (discord_user_id, display_name, COURSE_START, COURSE_END),
            )
            for mission in MISSIONS:
                db.execute(
                    """
                    INSERT OR IGNORE INTO mission_progress (discord_user_id, mission_id)
                    VALUES (?, ?)
                    """,
                    (discord_user_id, mission.mission_id),
                )

    def set_level(self, discord_user_id: str, level: int) -> None:
        with self.connect() as db:
            db.execute("UPDATE users SET level = ? WHERE discord_user_id = ?", (level, discord_user_id))

    def get_level(self, discord_user_id: str) -> int:
        with self.connect() as db:
            row = db.execute("SELECT level FROM users WHERE discord_user_id = ?", (discord_user_id,)).fetchone()
        return int(row["level"]) if row else 1

    def get_progress(self, discord_user_id: str) -> dict[str, MissionProgress]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT mission_id, pass_count, fail_count, completed
                FROM mission_progress
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchall()
        return {
            row["mission_id"]: MissionProgress(
                mission_id=row["mission_id"],
                pass_count=int(row["pass_count"]),
                fail_count=int(row["fail_count"]),
                completed=bool(row["completed"]),
            )
            for row in rows
        }

    def record_evaluation(self, discord_user_id: str, mission_id: str, result: str) -> MissionProgress:
        mission = get_mission(mission_id)
        if mission is None:
            raise ValueError(f"unknown mission: {mission_id}")

        progress = self.get_progress(discord_user_id).get(mission.mission_id, MissionProgress(mission.mission_id))
        updated = apply_evaluation(progress, result)
        updated = MissionProgress(mission.mission_id, updated.pass_count, updated.fail_count, updated.completed)

        with self.connect() as db:
            db.execute(
                """
                INSERT INTO mission_progress (discord_user_id, mission_id, pass_count, fail_count, completed, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(discord_user_id, mission_id)
                DO UPDATE SET
                    pass_count = excluded.pass_count,
                    fail_count = excluded.fail_count,
                    completed = excluded.completed,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (discord_user_id, mission.mission_id, updated.pass_count, updated.fail_count, int(updated.completed)),
            )
        return updated

    def save_weekly_report(self, discord_user_id: str, completed: str, study_hours: int, blockers: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO weekly_reports (discord_user_id, completed, study_hours, blockers)
                VALUES (?, ?, ?, ?)
                """,
                (discord_user_id, completed, study_hours, blockers),
            )
