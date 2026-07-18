from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from .missions import COURSE_END, COURSE_START, MISSIONS, get_mission
from .planner import MissionProgress, apply_evaluation

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        discord_user_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        level INTEGER NOT NULL DEFAULT 1,
        course_start TEXT NOT NULL,
        course_end TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mission_progress (
        discord_user_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        pass_count INTEGER NOT NULL DEFAULT 0,
        fail_count INTEGER NOT NULL DEFAULT 0,
        completed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (discord_user_id, mission_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_user_id TEXT NOT NULL,
        completed TEXT NOT NULL,
        study_hours INTEGER NOT NULL,
        blockers TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


class CoachStore:
    """미션 진행 상태 저장소.

    기본은 로컬 SQLite 파일이고, TURSO_DATABASE_URL이 설정되면
    Turso 임베디드 리플리카로 동작해서 서버가 재배포/재시작돼도
    데이터가 클라우드에 유지됩니다.
    """

    def __init__(self, db_path: str | Path, sync_url: str | None = None, auth_token: str | None = None) -> None:
        self.db_path = Path(db_path)
        self._use_turso = bool(sync_url)
        if self._use_turso:
            import libsql  # 배포 환경에서만 필요 (requirements.txt에 포함)

            self._db: Any = libsql.connect(str(self.db_path), sync_url=sync_url, auth_token=auth_token)
            self._db.sync()  # 부팅 시 클라우드에 저장된 데이터를 내려받음
        else:
            self._db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.init_db()

    @classmethod
    def from_env(cls) -> "CoachStore":
        return cls(
            os.getenv("CODYSSEY_DB_PATH", "codyssey_coach.sqlite3"),
            sync_url=os.getenv("TURSO_DATABASE_URL") or None,
            auth_token=os.getenv("TURSO_AUTH_TOKEN") or None,
        )

    def _commit(self) -> None:
        self._db.commit()
        if self._use_turso:
            try:
                self._db.sync()  # 쓰기 직후 클라우드로 푸시
            except Exception as error:  # 동기화 실패해도 봇은 계속 동작
                print(f"[storage] Turso sync 실패: {error}")

    def init_db(self) -> None:
        for statement in SCHEMA_STATEMENTS:
            self._db.execute(statement)
        self._commit()

    def ensure_user(self, discord_user_id: str, display_name: str) -> None:
        self._db.execute(
            """
            INSERT INTO users (discord_user_id, display_name, course_start, course_end)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(discord_user_id) DO UPDATE SET display_name = excluded.display_name
            """,
            (discord_user_id, display_name, COURSE_START, COURSE_END),
        )
        for mission in MISSIONS:
            self._db.execute(
                """
                INSERT OR IGNORE INTO mission_progress (discord_user_id, mission_id)
                VALUES (?, ?)
                """,
                (discord_user_id, mission.mission_id),
            )
        self._commit()

    def set_level(self, discord_user_id: str, level: int) -> None:
        self._db.execute("UPDATE users SET level = ? WHERE discord_user_id = ?", (level, discord_user_id))
        self._commit()

    def get_level(self, discord_user_id: str) -> int:
        row = self._db.execute(
            "SELECT level FROM users WHERE discord_user_id = ?", (discord_user_id,)
        ).fetchone()
        return int(row[0]) if row else 1

    def get_progress(self, discord_user_id: str) -> dict[str, MissionProgress]:
        rows = self._db.execute(
            """
            SELECT mission_id, pass_count, fail_count, completed
            FROM mission_progress
            WHERE discord_user_id = ?
            """,
            (discord_user_id,),
        ).fetchall()
        return {
            row[0]: MissionProgress(
                mission_id=row[0],
                pass_count=int(row[1]),
                fail_count=int(row[2]),
                completed=bool(row[3]),
            )
            for row in rows
        }

    def record_evaluation(self, discord_user_id: str, mission_id: str, result: str, pass_count: int = 1) -> MissionProgress:
        mission = get_mission(mission_id)
        if mission is None:
            raise ValueError(f"unknown mission: {mission_id}")

        progress = self.get_progress(discord_user_id).get(mission.mission_id, MissionProgress(mission.mission_id))
        updated = apply_evaluation(progress, result, pass_count)
        updated = MissionProgress(mission.mission_id, updated.pass_count, updated.fail_count, updated.completed)

        self._db.execute(
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
        self._commit()
        return updated

    def save_weekly_report(self, discord_user_id: str, completed: str, study_hours: int, blockers: str) -> None:
        self._db.execute(
            """
            INSERT INTO weekly_reports (discord_user_id, completed, study_hours, blockers)
            VALUES (?, ?, ?, ?)
            """,
            (discord_user_id, completed, study_hours, blockers),
        )
        self._commit()
