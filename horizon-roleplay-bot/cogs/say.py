import discord
from discord import app_commands
from discord.ext import commands


class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="say",
        description="Send a message as Horizon Roleplay.",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        message="The message for the bot to send.",
        channel="Optional channel to send it in.",
    )
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel | None = None,
    ):
        target = channel or interaction.channel

        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Choose a text channel.",
                ephemeral=True,
            )
            return

        await target.send(
            message,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await interaction.response.send_message(
            f"Message sent in {target.mention}.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Say(bot))
