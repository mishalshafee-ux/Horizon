import discord
from discord import app_commands
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="commands",
        description="View the Horizon Roleplay bot command guide.",
    )
    async def commands_guide(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Horizon Roleplay | Command Guide",
            description="Choose a command below to use the bot's features.",
            color=discord.Color.from_rgb(234, 197, 253),
        )

        embed.add_field(
            name="🎫 Tickets",
            value=(
                "`/ticket-panel` — Post the support panel. "
                "Requires Manage Server permission."
            ),
            inline=False,
        )
        embed.add_field(
            name="👋 Welcome",
            value="Welcome messages are sent automatically when a member joins.",
            inline=False,
        )
        embed.add_field(
            name="🗓️ Sessions",
            value=(
                "`/session-start` — Announce a session.\n"
                "`/session-end` — Mark the current session as ended.\n"
                "Both require the Session Host role."
            ),
            inline=False,
        )
        embed.add_field(
            name="✅ Verification",
            value=(
                "`/verify-panel` — Post the Roblox verification panel. "
                "Requires Manage Roles permission.\n"
                "Members use the panel button to verify their Roblox account."
            ),
            inline=False,
        )
        embed.add_field(
            name="📖 Bible Verses",
            value=(
                "`/verse` — Post a random Bible verse in this channel or "
                "a selected channel.\n"
                "A verse is also posted automatically every 24 hours."
            ),
            inline=False,
        )
        embed.set_footer(text="Horizon Roleplay")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
