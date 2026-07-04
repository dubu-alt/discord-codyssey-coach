from datetime import date

from codyssey_coach.planner import MissionProgress, apply_evaluation, build_status, current_week, remaining_weeks


def test_pass_three_times_completes_mission() -> None:
    progress = MissionProgress("B2-1")
    progress = apply_evaluation(progress, "pass")
    progress = apply_evaluation(progress, "pass")
    progress = apply_evaluation(progress, "pass")

    assert progress.pass_count == 3
    assert progress.completed is True


def test_fail_resets_pass_count() -> None:
    progress = MissionProgress("B2-1", pass_count=2)
    progress = apply_evaluation(progress, "fail")

    assert progress.pass_count == 0
    assert progress.fail_count == 1
    assert progress.completed is False


def test_course_week_calculation_for_july_fifth() -> None:
    today = date(2026, 7, 5)

    assert current_week(today) == 9
    assert remaining_weeks(today) == 17


def test_status_recommends_required_missions_first() -> None:
    status = build_status({}, today=date(2026, 7, 5), level=2)

    assert status.current_week == 9
    assert status.completed_required == 0
    assert status.next_missions[0].mission_id == "B1-1"
    assert status.optional_allowed is False
