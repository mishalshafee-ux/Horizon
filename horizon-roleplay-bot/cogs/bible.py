import asyncio

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config


API_URL = "https://bible-api.com/data/web/random"


async def fetch_random_verse() -> tuple[str, str] | None:
    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(API_URL) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                verse = data.get("random_verse", {})
                translation = data.get("translation", {})

                reference = (
                    f"{verse.get('book', 'Bible')} "
                    f"{verse.get('chapter', '')}:{verse.get('verse', '')}"
                ).strip()
                text = verse.get("text", "").strip()
                translation_name = translation.get("name", "World English Bible")

                if not reference or not text:
                    return None

                return reference, f"{text}\n\n— {reference} ({translation_name})"

    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None


def make_verse_embed(reference: str, text: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"📖 {reference}",
        description=text,
        color=discord.Color.from_rgb(234, 197, 253),
    )
    embed.set_footer(text="Horizon Roleplay • World English Bible")
    return embed


class Bible(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_verse.start()

    def cog_unload(self):
        self.daily_verse.cancel()

    @tasks.loop(hours=24)
    async def daily_verse(self):
        channel = self.bot.get_channel(config.BIBLE_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            print("Daily Bible verse skipped: BIBLE_CHANNEL_ID is missing or invalid.")
            return

        result = await fetch_random_verse()
        if result is None:
            print("Daily Bible verse skipped: verse API request failed.")
            return

        reference, text = result
        await channel.send(embed=make_verse_embed(reference, text))

    @daily_verse.before_loop
    async def before_daily_verse(self):
        await self.bot.wait_until_ready()
        # Wait a full 24 hours before the first scheduled post.
        await asyncio.sleep(24 * 60 * 60)

    @app_commands.command(
        name="verse",
        description="Post a random Bible verse.",
    )
    @app_commands.describe(
        channel="Where to post the verse. Leave blank to use this channel."
    )
    async def verse(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ):
        target = channel or interaction.channel

        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Choose a text channel for the verse.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        result = await fetch_random_verse()
        if result is None:
            await interaction.followup.send(
                "I couldn't fetch a verse right now. Please try again shortly.",
                ephemeral=True,
            )
            return

        reference, text = result
        await target.send(embed=make_verse_embed(reference, text))
        await interaction.followup.send(
            f"Posted **{reference}** in {target.mention}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Bible(bot))
