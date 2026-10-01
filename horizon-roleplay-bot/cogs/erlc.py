import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config


API_URL = "https://api.erlc.gg/v2/server"


class ERLCAPIError(Exception):
    pass


async def get_server_data(*, include_players=False):
    if not config.ERLC_API_KEY:
        raise ERLCAPIError("ERLC_API_KEY is not set in Wispbyte.")

    params = {"Staff": "true", "Queue": "true"}
    if include_players:
        params["Players"] = "true"

    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                API_URL,
                headers={"server-key": config.ERLC_API_KEY},
                params=params,
            ) as response:
                data = await response.json(content_type=None)

                if response.status != 200:
                    message = data.get("message") or data.get("error")
                    raise ERLCAPIError(
                        message or f"ER:LC API returned HTTP {response.status}."
                    )

                return data
    except aiohttp.ClientError as error:
        raise ERLCAPIError("Could not connect to the ER:LC API.") from error
    except ValueError as error:
        raise ERLCAPIError("The ER:LC API returned an invalid response.") from error


class ERLCInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="erlc-info",
        description="Show live Horizon Roleplay server information.",
    )
    async def erlc_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            data = await get_server_data()
        except ERLCAPIError as error:
            await interaction.followup.send(
                f"ER:LC info unavailable: {error}",
                ephemeral=True,
            )
            return

        staff = data.get("Staff") or {}
        queue = data.get("Queue") or []

        embed = discord.Embed(
            title="Horizon Roleplay | Live Server Info",
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.add_field(
            name="Server",
            value=(
                f"**Name:** {data.get('Name', 'Horizon Roleplay')}\n"
                f"**Code:** `{data.get('JoinKey', 'Horrp')}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Players",
            value=f"{data.get('CurrentPlayers', 0)}/{data.get('MaxPlayers', '?')}",
            inline=True,
        )
        embed.add_field(name="Queue", value=str(len(queue)), inline=True)
        embed.add_field(
            name="Moderators",
            value=str(len(staff.get("Mods") or {})),
            inline=True,
        )
        embed.set_footer(text="Live data from the ER:LC API")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="erlc-players",
        description="List current Horizon Roleplay players.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def erlc_players(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            data = await get_server_data(include_players=True)
        except ERLCAPIError as error:
            await interaction.followup.send(
                f"Player list unavailable: {error}",
                ephemeral=True,
            )
            return

        players = data.get("Players") or []
        if not players:
            await interaction.followup.send(
                "There are no players in the server right now.",
                ephemeral=True,
            )
            return

        lines = []
        for player in players[:40]:
            name = str(player.get("Player", "Unknown")).split(":")[0]
            team = player.get("Team", "Unknown")
            lines.append(f"• **{name}** — {team}")

        embed = discord.Embed(
            title=f"Horizon Roleplay | Players ({len(players)})",
            description="\n".join(lines),
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.set_footer(text="Staff-only command")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ERLCInfo(bot))
