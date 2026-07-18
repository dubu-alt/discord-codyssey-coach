from __future__ import annotations

from .missions import MISSIONS, PASS_REQUIRED, get_mission
from .planner import CourseStatus, MissionProgress


def mission_board_message(progress_by_id: dict[str, MissionProgress]) -> str:
    """전체 미션 현황을 한눈에 보여주는 메시지."""

    def line(mission) -> str:
        progress = progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id))
        if progress.completed:
            symbol, note = "✅", "완료"
        elif progress.pass_count > 0:
            symbol, note = "🔶", f"{progress.pass_count}/{PASS_REQUIRED} Pass"
        else:
            symbol, note = "⬜", "미시작"
        return f"{symbol} {mission.mission_id} {mission.name} — {note}"

    required = [mission for mission in MISSIONS if mission.required]
    optional = [mission for mission in MISSIONS if not mission.required]
    done_required = sum(
        1 for mission in required
        if progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id)).completed
    )
    required_lines = "\n".join(line(mission) for mission in required)
    optional_lines = "\n".join(line(mission) for mission in optional)
    percent = round(done_required / len(required) * 100)
    return (
        f"미션 현황 (필수 {done_required}/{len(required)} 완료, 진행률 {percent}%)\n\n"
        f"[필수 미션]\n{required_lines}\n\n"
        f"[선택 미션]\n{optional_lines}"
    )


def mission_label(mission_id: str) -> str:
    mission = get_mission(mission_id)
    return f"{mission.mission_id} {mission.name}" if mission else mission_id


def evaluation_message(mission_id: str, result: str, progress: MissionProgress, count: int = 1) -> str:
    label = mission_label(mission_id)
    if result.lower() == "fail":
        return (
            f"{label}에서 Fail을 기록했어요.\n\n"
            f"Pass 카운트가 0/{PASS_REQUIRED}으로 초기화됩니다.\n"
            "다음 제출 전에는 평가 기준을 다시 점검하고 재도전하는 것이 좋아요."
        )

    pass_note = f"Pass {count}회를" if count > 1 else "Pass를"
    if progress.completed:
        return (
            f"{label} {pass_note} 기록했어요.\n\n"
            f"현재 평가 상태: {PASS_REQUIRED}/{PASS_REQUIRED} Pass\n"
            "이 미션은 완료 처리되었습니다."
        )

    left = PASS_REQUIRED - progress.pass_count
    return (
        f"{label} {pass_note} 기록했어요.\n\n"
        f"현재 평가 상태: {progress.pass_count}/{PASS_REQUIRED} Pass\n"
        f"앞으로 {left}번 더 Pass를 받으면 완료됩니다."
    )


def status_message(display_name: str, level: int, status: CourseStatus) -> str:
    next_lines = "\n".join(f"{index}. {mission.mission_id} - {mission.name}" for index, mission in enumerate(status.next_missions, 1))
    optional = "가능" if status.optional_allowed else "보류 추천"
    return (
        f"{display_name}님의 Codyssey 상태입니다.\n\n"
        f"현재 주차: {status.current_week}/26주\n"
        f"남은 주차: {status.remaining_weeks}주\n"
        f"Level: {level}\n"
        f"필수 미션 완료: {status.completed_required}/{status.total_required}\n"
        f"진행률: {status.progress_percent}%\n"
        f"일정 상태: {status.risk_level}\n"
        f"선택 미션: {optional}\n\n"
        f"{status.risk_message}\n\n"
        f"다음 우선순위:\n{next_lines or '현재 추천할 남은 필수 미션이 없습니다.'}"
    )


def weekly_plan_message(status: CourseStatus) -> str:
    next_lines = "\n".join(f"{index}. {mission.mission_id} - {mission.name}" for index, mission in enumerate(status.next_missions, 1))
    optional_note = (
        "선택 미션을 1개 병행해도 괜찮습니다."
        if status.optional_allowed
        else "이번 주는 선택 미션보다 필수 미션과 평가 Pass 확보에 집중하는 편이 좋습니다."
    )
    return (
        "다음 주 계획을 계산했어요.\n\n"
        f"일정 상태: {status.risk_level}\n"
        f"{status.risk_message}\n\n"
        f"우선순위:\n{next_lines or '남은 필수 미션이 없습니다.'}\n\n"
        f"{optional_note}"
    )
