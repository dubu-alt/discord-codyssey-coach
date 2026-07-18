from __future__ import annotations

import asyncio
import os
from datetime import date
from pathlib import Path

import aiohttp
import certifi
import discord
from aiohttp import web
from discord import app_commands

from .messages import evaluation_message, mission_board_message, status_message, weekly_plan_message
from .missions import MISSIONS, PASS_REQUIRED, get_mission
from .planner import CourseStatus, MissionProgress, build_status
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


async def start_health_server(port: int) -> None:
    """호스팅 플랫폼의 헬스체크와 keep-alive 핑을 받는 작은 웹 서버."""
    app = web.Application()

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"Health server listening on port {port}")


async def keep_alive(url: str, interval_seconds: int = 600) -> None:
    """무료 인스턴스가 잠들지 않도록 주기적으로 자기 자신을 핑."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as response:
                    await response.read()
            except Exception as error:
                print(f"[keep-alive] 핑 실패: {error}")
            await asyncio.sleep(interval_seconds)


def create_bot() -> discord.Client:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    store = CoachStore.from_env()

    async def setup_hook() -> None:
        await start_health_server(int(os.getenv("PORT", "8080")))
        keep_alive_url = os.getenv("KEEP_ALIVE_URL")
        if keep_alive_url:
            client.loop.create_task(keep_alive(keep_alive_url))

    client.setup_hook = setup_hook  # type: ignore[method-assign]

    # DB 작업(특히 Turso 동기화)은 네트워크 왕복이 있어 디스코드의 3초 응답 제한을
    # 넘길 수 있습니다. 모든 명령은 defer()로 먼저 응답하고, DB 작업은 별도 스레드에서
    # 실행한 뒤 followup으로 결과를 보냅니다. DB 작업이 DB_TIMEOUT초를 넘기면
    # 자동으로 취소하고 사용자에게 재시도를 안내합니다.

    DB_TIMEOUT = 15.0

    async def run_db(func, *args):
        return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=DB_TIMEOUT)

    async def ensure(interaction: discord.Interaction) -> str:
        user_id = str(interaction.user.id)
        await run_db(store.ensure_user, user_id, interaction.user.display_name)
        return user_id

    async def load_status(user_id: str) -> tuple[int, CourseStatus]:
        def _load() -> tuple[int, dict]:
            return store.get_level(user_id), store.get_progress(user_id)

        level, progress = await run_db(_load)
        return level, build_status(progress, today=date.today(), level=level)

    @tree.error
    async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        original = getattr(error, "original", error)
        if isinstance(original, (asyncio.TimeoutError, TimeoutError)):
            message = "처리가 너무 오래 걸려서 요청을 취소했어요. 잠시 후 다시 시도해주세요."
        else:
            message = "요청 처리 중 문제가 발생했어요. 잠시 후 다시 시도해주세요."
        print(f"[command-error] {interaction.command.name if interaction.command else '?'}: {error}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message)
            else:
                await interaction.response.send_message(message)
        except discord.HTTPException:
            pass

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
        await interaction.response.defer()
        user_id = await ensure(interaction)
        level, status = await load_status(user_id)
        await interaction.followup.send(status_message(interaction.user.display_name, level, status))

    @tree.command(name="레벨설정", description="현재 Codyssey 레벨을 기록합니다.")
    @app_commands.describe(level="현재 레벨")
    async def set_level(interaction: discord.Interaction, level: app_commands.Range[int, 1, 10]) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        await run_db(store.set_level, user_id, int(level))
        await interaction.followup.send(f"현재 레벨을 {level}로 기록했어요.")

    def _mission_choice(mission, progress_by_id) -> app_commands.Choice[str]:
        progress = progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id))
        if progress.completed:
            note = "완료"
        elif progress.pass_count > 0:
            note = f"{progress.pass_count}/{PASS_REQUIRED} Pass"
        else:
            note = "미시작"
        name = f"{mission.mission_id} {mission.name} ({note})"
        return app_commands.Choice(name=name[:100], value=mission.mission_id)

    async def incomplete_missions_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """평가결과용: 아직 완료하지 않은 미션만 현재 Pass 횟수와 함께 표시."""
        progress_by_id = await run_db(store.get_progress, str(interaction.user.id))
        keyword = current.strip().lower()
        choices = [
            _mission_choice(mission, progress_by_id)
            for mission in MISSIONS
            if not progress_by_id.get(mission.mission_id, MissionProgress(mission.mission_id)).completed
        ]
        if keyword:
            choices = [choice for choice in choices if keyword in choice.name.lower()]
        return choices[:25]

    async def all_missions_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """기록수정용: 완료 포함 전체 미션을 현재 상태와 함께 표시."""
        progress_by_id = await run_db(store.get_progress, str(interaction.user.id))
        keyword = current.strip().lower()
        choices = [_mission_choice(mission, progress_by_id) for mission in MISSIONS]
        if keyword:
            choices = [choice for choice in choices if keyword in choice.name.lower()]
        return choices[:25]

    @tree.command(name="미션현황", description="전체 미션의 완료/진행 상태를 한눈에 확인합니다.")
    async def mission_board(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        progress_by_id = await run_db(store.get_progress, user_id)
        await interaction.followup.send(mission_board_message(progress_by_id))

    @tree.command(name="평가결과", description="미션 평가 결과를 기록합니다. Pass 3회면 완료, Fail이면 초기화됩니다.")
    @app_commands.describe(mission_id="미션 선택 (미완료 미션만 표시)", result="평가 결과", pass_count="한 번에 기록할 Pass 횟수")
    @app_commands.autocomplete(mission_id=incomplete_missions_autocomplete)
    @app_commands.choices(
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
        mission_id: str,
        result: app_commands.Choice[str],
        pass_count: app_commands.Choice[int] | None = None,
    ) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        mission = get_mission(mission_id)
        if mission is None:
            await interaction.followup.send(f"'{mission_id}' 미션을 찾지 못했어요. 목록에서 선택해주세요.")
            return
        count = pass_count.value if pass_count else 1
        progress = await run_db(store.record_evaluation, user_id, mission.mission_id, result.value, count)
        _, status = await load_status(user_id)
        summary = f"\n\n전체 진행: 필수 미션 {status.completed_required}/{status.total_required} 완료 ({status.progress_percent}%)"
        await interaction.followup.send(evaluation_message(mission.mission_id, result.value, progress, count) + summary)

    @tree.command(name="기록수정", description="잘못 기록한 미션의 Pass 카운트를 직접 수정합니다.")
    @app_commands.describe(mission_id="수정할 미션", pass_count="설정할 Pass 횟수 (3이면 완료 처리, 0이면 초기화)")
    @app_commands.autocomplete(mission_id=all_missions_autocomplete)
    async def fix_record(
        interaction: discord.Interaction,
        mission_id: str,
        pass_count: app_commands.Range[int, 0, 3],
    ) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        mission = get_mission(mission_id)
        if mission is None:
            await interaction.followup.send(f"'{mission_id}' 미션을 찾지 못했어요. 목록에서 선택해주세요.")
            return
        progress = await run_db(store.set_mission_progress, user_id, mission.mission_id, int(pass_count))
        state = "완료 처리되었습니다." if progress.completed else f"{progress.pass_count}/{PASS_REQUIRED} Pass 상태입니다."
        await interaction.followup.send(f"{mission.mission_id} {mission.name} 기록을 수정했어요. 현재 {state}")

    @tree.command(name="주간보고", description="이번 주 완료 내용, 학습 시간, 막힌 점을 기록합니다.")
    @app_commands.describe(completed="이번 주 완료한 내용", study_hours="이번 주 학습 시간", blockers="막힌 점")
    async def weekly_report(interaction: discord.Interaction, completed: str, study_hours: app_commands.Range[int, 0, 168], blockers: str = "없음") -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        await run_db(store.save_weekly_report, user_id, completed, int(study_hours), blockers)
        _, status = await load_status(user_id)
        await interaction.followup.send("이번 주 보고를 저장했어요.\n\n" + weekly_plan_message(status))

    @tree.command(name="다음주계획", description="남은 기간과 필수 미션 기준으로 다음 주 우선순위를 추천합니다.")
    async def next_week(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        _, status = await load_status(user_id)
        await interaction.followup.send(weekly_plan_message(status))

    @tree.command(name="위험도", description="기초 단계 종료일까지의 일정 위험도를 확인합니다.")
    async def risk(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        user_id = await ensure(interaction)
        _, status = await load_status(user_id)
        await interaction.followup.send(
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
