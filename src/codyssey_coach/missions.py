from __future__ import annotations

from dataclasses import dataclass


COURSE_START = "2026-05-07"
COURSE_END = "2026-10-31"
TOTAL_WEEKS = 26
PASS_REQUIRED = 3


@dataclass(frozen=True)
class Mission:
    mission_id: str
    name: str
    required: bool
    hours: int
    order: int
    unlock_after_exam: bool = False


MISSIONS: tuple[Mission, ...] = (
    Mission("B1-1", "시스템 관제 자동화 스크립트 개발", True, 40, 1),
    Mission("B1-2", "리눅스 프로세스 및 시스템 리소스 트러블슈팅", True, 40, 2),
    Mission("B2-1", "파일 기반 가계부 콘솔 프로그램 만들기", True, 60, 3),
    Mission("B2-2", "실전 Git 협업 워크플로우 / Team 미션", True, 20, 4),
    Mission("B3-1", "Mini Redis 구축", True, 80, 5),
    Mission("B3-2", "Mini Git 구축", True, 80, 6),
    Mission("B4-1", "웹 기초 완성, 나만의 포트폴리오 구축", True, 80, 7),
    Mission("B4-2", "React 핵심 개념 마스터: SPA 서비스 구현", False, 80, 8),
    Mission("B5-1", "SQL로 만드는 나만의 데이터베이스", True, 40, 9),
    Mission("B5-2", "FastAPI 기반 CRUD 웹 서비스 구축", False, 60, 10),
    Mission("B5-3", "인증과 연관관계로 완성하는 FastAPI 웹 서비스", False, 60, 11),
    Mission("B6-1", "클라우드 환경에서 웹 서비스 인프라 구축", True, 40, 12),
    Mission("B6-2", "AI 기반 Git 커밋 & PR 자동 생성기 개발", True, 40, 13),
    Mission("TEST", "시험 평가", True, 0, 14),
    Mission("B7-1", "[Project A] 웹 기반 AI 챗봇 서비스 개발", True, 120, 15, True),
    Mission("B7-2", "[Project B] 웹 기반 AI 챗봇 서비스 고도화 프로젝트", False, 120, 16, True),
)


def get_mission(mission_id: str) -> Mission | None:
    normalized = mission_id.strip().upper()
    return next((mission for mission in MISSIONS if mission.mission_id == normalized), None)


def required_missions() -> list[Mission]:
    return [mission for mission in MISSIONS if mission.required]


def optional_missions() -> list[Mission]:
    return [mission for mission in MISSIONS if not mission.required]
