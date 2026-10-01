import discord
from discord import app_commands
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="commands",
        description="View the Horizon Roleplay bot command guide.",
    )
    async def commands_guide(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Horizon Roleplay | Command Guide",
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.add_field(
            name="Tickets",
            value="`!ticket-panel` — Post the support panel. Requires Manage Server.",
            inline=False,
        )
        embed.add_field(
            name="Sessions",
            value=(
                "`/session-start` — Post the session vote and live server count.\n"
                "`/session-end` — Close the vote. Both require Session Host."
            ),
            inline=False,
        )
        embed.add_field(
            name="ER:LC",
            value=(
                "`/erlc-info` — Show live server info.\n"
                "`/erlc-players` — List online players. Requires Manage Server."
            ),
            inline=False,
        )
        embed.add_field(
            name="Other",
            value=(
                "`/say` — Send a message as the bot. Requires Manage Messages.\n"
                "`/verse` — Post a Bible verse.\n"
                "`/verify-panel` — Post the Roblox verification panel."
            ),
            inline=False,
        )
        embed.set_footer(text="Horizon Roleplay")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Commands(bot))
