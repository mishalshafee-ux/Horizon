from datetime import timedelta
import re
import os
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



    @commands.command(name="addrole")
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        owner_id = int(os.getenv("BOT_OWNER_ID", "0") or 0)
        if ctx.author.id != owner_id:
            return

        if role >= ctx.guild.me.top_role:
            await ctx.reply("I can't assign a role at or above my highest role.")
            return

        try:
            await member.add_roles(role, reason=f"Role assigned by bot owner {ctx.author}")
        except discord.Forbidden:
            await ctx.reply("I don't have permission to assign that role.")
            return
        except discord.HTTPException:
            await ctx.reply("Discord couldn't assign that role. Please try again.")
            return

        await ctx.reply(f"Added **{role.name}** to {member.mention}.")

    @commands.command(name="addtimeout")
    async def addtimeout(self, ctx, member: discord.Member, duration: str, *, reason: str):
        # Remove the public command message to keep the action discreet.
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        owner_id = int(os.getenv("BOT_OWNER_ID", "0") or 0)
        is_owner = ctx.author.id == owner_id and owner_id != 0
        is_admin = ctx.author.guild_permissions.administrator

        async def private_reply(message):
            try:
                await ctx.author.send(message)
            except discord.Forbidden:
                pass

        if not (is_owner or is_admin):
            await private_reply("You are not authorized to use this moderation command.")
            return

        if ctx.guild is None or member.guild != ctx.guild:
            await private_reply("Use this command in the server with a valid member.")
            return

        match = re.fullmatch(r"([1-9][0-9]*)([smhd])", duration.lower())
        if not match:
            await private_reply("Duration format: `10m`, `2h`, or `1d` (maximum 28d).")
            return

        amount = int(match.group(1))
        unit = match.group(2)
        seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        seconds = amount * seconds_per_unit[unit]

        if seconds > 28 * 86400:
            await private_reply("Discord timeouts cannot exceed 28 days.")
            return

        bot_member = ctx.guild.me
        if bot_member is None or not bot_member.guild_permissions.moderate_members:
            await private_reply("The bot needs the **Moderate Members** permission.")
            return

        if member == ctx.guild.owner or member.top_role >= bot_member.top_role:
            await private_reply("I can't timeout the server owner or a member with an equal/higher role.")
            return

        try:
            await member.timeout(
                timedelta(seconds=seconds),
                reason=f"{reason[:400]}",
            )
        except discord.Forbidden:
            await private_reply("Discord denied the timeout. Check the bot's role and permissions.")
            return
        except discord.HTTPException:
            await private_reply("Discord couldn't apply that timeout. Try again.")
            return

        await private_reply(
            f"Timeout applied to {member} for {duration}. Reason: {reason}"
        )

async def setup(bot):
    await bot.add_cog(Commands(bot))
