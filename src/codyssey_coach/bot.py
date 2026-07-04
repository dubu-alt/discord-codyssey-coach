from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import certifi
import discord
from discord import app_commands

from .messages import evaluation_message, status_message, weekly_plan_message
from .missions import MISSIONS, get_mission
from .planner import build_status
from .storage import CoachStore


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_bot() -> discord.Client:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    store = CoachStore(os.getenv("CODYSSEY_DB_PATH", "codyssey_coach.sqlite3"))

    async def ensure(interaction: discord.Interaction) -> str:
        user_id = str(interaction.user.id)
        store.ensure_user(user_id, interaction.user.display_name)
        return user_id

    @client.event
    async def on_ready() -> None:
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        else:
            await tree.sync()
        print(f"Codyssey coach bot is ready as {client.user}")

    @tree.command(name="내상태", description="현재 Codyssey 진행 상태와 일정 위험도를 확인합니다.")
    async def my_status(interaction: discord.Interaction) -> None:
        user_id = await ensure(interaction)
        level = store.get_level(user_id)
        status = build_status(store.get_progress(user_id), today=date.today(), level=level)
        await interaction.response.send_message(status_message(interaction.user.display_name, level, status))

    @tree.command(name="레벨설정", description="현재 Codyssey 레벨을 기록합니다.")
    @app_commands.describe(level="현재 레벨")
    async def set_level(interaction: discord.Interaction, level: app_commands.Range[int, 1, 10]) -> None:
        user_id = await ensure(interaction)
        store.set_level(user_id, int(level))
        await interaction.response.send_message(f"현재 레벨을 {level}로 기록했어요.")

    @tree.command(name="평가결과", description="미션 평가 결과를 기록합니다. Pass 3회면 완료, Fail이면 초기화됩니다.")
    @app_commands.describe(mission_id="미션 선택", result="평가 결과", pass_count="한 번에 기록할 Pass 횟수")
    @app_commands.choices(
        mission_id=[
            app_commands.Choice(name=f"{mission.mission_id} - {mission.name}", value=mission.mission_id)
            for mission in MISSIONS
        ],
        result=[
            app_commands.Choice(name="pass", value="pass"),
            app_commands.Choice(name="fail", value="fail"),
        ],
        pass_count=[
            app_commands.Choice(name="1회", value=1),
            app_commands.Choice(name="2회", value=2),
            app_commands.Choice(name="3회", value=3),
        ],
    )
    async def evaluation(
        interaction: discord.Interaction,
        mission_id: app_commands.Choice[str],
        result: app_commands.Choice[str],
        pass_count: app_commands.Choice[int] | None = None,
    ) -> None:
        user_id = await ensure(interaction)
        mission = get_mission(mission_id.value)
        if mission is None:
            await interaction.response.send_message(f"'{mission_id.value}' 미션을 찾지 못했어요.", ephemeral=True)
            return
        count = pass_count.value if pass_count else 1
        progress = store.record_evaluation(user_id, mission.mission_id, result.value, count)
        await interaction.response.send_message(evaluation_message(mission.mission_id, result.value, progress, count))

    @tree.command(name="주간보고", description="이번 주 완료 내용, 학습 시간, 막힌 점을 기록합니다.")
    @app_commands.describe(completed="이번 주 완료한 내용", study_hours="이번 주 학습 시간", blockers="막힌 점")
    async def weekly_report(interaction: discord.Interaction, completed: str, study_hours: app_commands.Range[int, 0, 168], blockers: str = "없음") -> None:
        user_id = await ensure(interaction)
        store.save_weekly_report(user_id, completed, int(study_hours), blockers)
        level = store.get_level(user_id)
        status = build_status(store.get_progress(user_id), today=date.today(), level=level)
        await interaction.response.send_message("이번 주 보고를 저장했어요.\n\n" + weekly_plan_message(status))

    @tree.command(name="다음주계획", description="남은 기간과 필수 미션 기준으로 다음 주 우선순위를 추천합니다.")
    async def next_week(interaction: discord.Interaction) -> None:
        user_id = await ensure(interaction)
        level = store.get_level(user_id)
        status = build_status(store.get_progress(user_id), today=date.today(), level=level)
        await interaction.response.send_message(weekly_plan_message(status))

    @tree.command(name="위험도", description="기초 단계 종료일까지의 일정 위험도를 확인합니다.")
    async def risk(interaction: discord.Interaction) -> None:
        user_id = await ensure(interaction)
        level = store.get_level(user_id)
        status = build_status(store.get_progress(user_id), today=date.today(), level=level)
        await interaction.response.send_message(
            f"일정 상태: {status.risk_level}\n"
            f"현재 주차: {status.current_week}/26주\n"
            f"남은 주차: {status.remaining_weeks}주\n"
            f"필수 미션 완료: {status.completed_required}/{status.total_required}\n\n"
            f"{status.risk_message}"
        )

    return client


def main() -> None:
    load_dotenv()
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is required.")
    create_bot().run(token)


if __name__ == "__main__":
    main()
