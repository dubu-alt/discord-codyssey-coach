from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import ceil

from .missions import COURSE_END, COURSE_START, MISSIONS, PASS_REQUIRED, TOTAL_WEEKS, Mission


@dataclass(frozen=True)
class MissionProgress:
    mission_id: str
    pass_count: int = 0
    fail_count: int = 0
    completed: bool = False


@dataclass(frozen=True)
class CourseStatus:
    current_week: int
    remaining_weeks: int
    progress_percent: int
    completed_required: int
    total_required: int
    risk_level: str
    risk_message: str
    next_missions: list[Mission]
    optional_allowed: bool


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def current_week(today: date | None = None) -> int:
    today = today or date.today()
    start = parse_date(COURSE_START)
    if today <= start:
        return 1
    return min(TOTAL_WEEKS, ((today - start).days // 7) + 1)


def remaining_weeks(today: date | None = None) -> int:
    today = today or date.today()
    end = parse_date(COURSE_END)
    if today >= end:
        return 0
    return max(0, ceil((end - today).days / 7))


def apply_evaluation(progress: MissionProgress | None, result: str, pass_count: int = 1) -> MissionProgress:
    current = progress or MissionProgress(mission_id="")
    normalized = result.strip().lower()
    if normalized == "pass":
        pass_count = min(PASS_REQUIRED, current.pass_count + pass_count)
        return MissionProgress(
            mission_id=current.mission_id,
            pass_count=pass_count,
            fail_count=current.fail_count,
            completed=pass_count >= PASS_REQUIRED,
        )
    if normalized == "fail":
        return MissionProgress(
            mission_id=current.mission_id,
            pass_count=0,
            fail_count=current.fail_count + 1,
            completed=False,
        )
    raise ValueError("result must be 'pass' or 'fail'")


def build_status(progress_by_id: dict[str, MissionProgress], today: date | None = None, level: int = 1) -> CourseStatus:
    required = [mission for mission in MISSIONS if mission.required]
    completed_required = sum(1 for mission in required if progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id)).completed)
    total_required = len(required)
    progress_percent = round((completed_required / total_required) * 100)
    left_required = total_required - completed_required
    weeks_left = remaining_weeks(today)

    needed_per_week = left_required / max(weeks_left, 1)
    if weeks_left <= 0 and left_required > 0:
        risk_level = "위험"
        risk_message = "기초 단계 종료일이 지났거나 오늘입니다. 남은 필수 미션을 즉시 정리해야 합니다."
    elif needed_per_week >= 1.0:
        risk_level = "위험"
        risk_message = "남은 주차 대비 필수 미션이 많습니다. 선택 미션은 보류하고 필수 미션만 진행하세요."
    elif needed_per_week >= 0.6:
        risk_level = "주의"
        risk_message = "약간 빠듯합니다. 이번 주는 필수 미션 완료와 평가 Pass 확보를 우선하세요."
    else:
        risk_level = "안정"
        risk_message = "현재 속도는 안정적입니다. 필수 미션 흐름을 유지하면 선택 미션도 검토할 수 있습니다."

    next_missions = recommend_next_missions(progress_by_id, level)
    optional_allowed = risk_level == "안정" and weeks_left >= 3

    return CourseStatus(
        current_week=current_week(today),
        remaining_weeks=weeks_left,
        progress_percent=progress_percent,
        completed_required=completed_required,
        total_required=total_required,
        risk_level=risk_level,
        risk_message=risk_message,
        next_missions=next_missions,
        optional_allowed=optional_allowed,
    )


def recommend_next_missions(progress_by_id: dict[str, MissionProgress], level: int = 1) -> list[Mission]:
    recommendations: list[Mission] = []
    exam_completed = progress_by_id.get("TEST", MissionProgress("TEST")).completed

    for mission in MISSIONS:
        mission_progress = progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id))
        if mission_progress.completed:
            continue
        if mission.unlock_after_exam and not exam_completed:
            continue
        if mission.mission_id == "TEST" and level < 5:
            continue
        if mission.required or mission_progress.pass_count > 0:
            recommendations.append(mission)
        if len(recommendations) == 3:
            break

    return recommendations
