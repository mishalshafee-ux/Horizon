import os
import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from .erlc import ERLCAPIError, get_server_data


try:
    REQUIRED_VOTES = max(1, int(os.getenv("SESSION_REQUIRED_VOTES", "5")))
except ValueError:
    REQUIRED_VOTES = 5

ORANGE = getattr(config, "EMBED_COLOR", 0xF28C28)


class SessionVoteView(discord.ui.View):
    def __init__(self, cog, channel):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel = channel
        self.voters = set()
        self.completed = False

    @discord.ui.button(
        label="Vote to Join",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="horizon:session_vote_to_join",
    )
    async def vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.completed:
            await interaction.response.send_message(
                "This session vote has ended.",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.voters:
            self.voters.remove(interaction.user.id)
            reply = "Your vote was removed."
        else:
            self.voters.add(interaction.user.id)
            reply = "Your vote was counted."

        poll_embed = interaction.message.embeds[0].copy()
        poll_embed.set_field_at(
            0,
            name="Votes",
            value=f"{len(self.voters)}/{REQUIRED_VOTES}",
            inline=True,
        )

        passed = len(self.voters) >= REQUIRED_VOTES
        if passed:
            self.completed = True
            for item in self.children:
                item.disabled = True
            poll_embed.set_field_at(
                1,
                name="Status",
                value="🟢 Vote passed — starting session",
                inline=True,
            )

        await interaction.response.edit_message(embed=poll_embed, view=self)
        await interaction.followup.send(reply, ephemeral=True)

        if passed:
            self.cog.vote_view = None
            await self.cog.start_session(self.channel, len(self.voters))


class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_message = None
        self.vote_view = None
        self.session_message = None

    async def require_session_host(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Use this command in the Horizon Roleplay server.",
                ephemeral=True,
            )
            return False

        if not any(
            role.id == config.SESSION_HOST_ROLE_ID
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "You need the Session Host role to use this command.",
                ephemeral=True,
            )
            return False

        return True

    def get_session_channel(self, guild):
        channel = guild.get_channel(config.SESSION_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def start_session(self, channel, vote_count: int, forced: bool = False):
        if self.session_message is not None:
            return

        try:
            data = await get_server_data()
            player_count = (
                f"{data.get('CurrentPlayers', 0)}/"
                f"{data.get('MaxPlayers', '?')}"
            )
            server_code = data.get("JoinKey") or getattr(
                config, "SERVER_CODE", "Horrp"
            )
            queue_count = len(data.get("Queue") or [])
            staff = data.get("Staff") or {}
            staff_count = len(staff.get("Mods") or [])
        except ERLCAPIError:
            player_count = "Unavailable"
            server_code = getattr(config, "SERVER_CODE", "Horrp")
            queue_count = "Unavailable"
            staff_count = "Unavailable"

        rules_url = getattr(config, "GAME_RULES_URL", "")
        rules = (
            f"[Horizon Roleplay game rules]({rules_url})"
            if rules_url
            else "Horizon Roleplay game rules"
        )

        embed = discord.Embed(
            title="Session Information",
            description=(
                "> Sessions are hosted by our **Session Hosts** and take place "
                "when staff are available. Please review the information below "
                "before joining."
            ),
            color=ORANGE,
        )
        embed.add_field(
            name="Server Details",
            value=(
                f"**Server Name:** `{getattr(config, 'SERVER_NAME', 'Horizon Roleplay')}`\n"
                f"**Server Code:** `{server_code}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Live Server Activity",
            value=(
                f"**In-game Players:** `{player_count}`\n"
                f"**Currently Moderating:** `{staff_count}`\n"
                f"**In-Queue Players:** `{queue_count}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Session Vote",
            value=(
                f"✅ Passed with **{vote_count}** votes."
                if not forced
                else f"⚠️ Started early by a Session Host. **{vote_count}** votes were recorded."
            ),
            inline=False,
        )
        embed.add_field(
            name="Last Updated",
            value=f"<t:{int(time.time())}:R>",
            inline=False,
        )
        embed.add_field(
            name="Before Joining",
            value=f"Please review the {rules} before joining.",
            inline=False,
        )
        embed.set_footer(text="Horizon Roleplay • Hosted by Session Hosts")

        banner_url = getattr(config, "SESSION_BANNER_URL", "")
        embeds = []
        if banner_url:
            banner = discord.Embed(color=ORANGE)
            banner.set_image(url=banner_url)
            embeds.append(banner)
        embeds.append(embed)

        role_id = getattr(config, "SESSION_NOTIFICATION_ROLE_ID", 0)

        role = channel.guild.get_role(role_id) if role_id else None
        content = role.mention if role else None

        self.session_message = await channel.send(
            content=content,
            embeds=embeds,
            allowed_mentions=discord.AllowedMentions(
                roles=True,
                users=False,
                everyone=False,
            ),
        )

    @app_commands.command(
        name="session-vote",
        description="Open a vote to decide whether to start a session.",
    )
    async def session_vote(self, interaction: discord.Interaction):
        if not await self.require_session_host(interaction):
            return

        if self.vote_view is not None or self.session_message is not None:
            await interaction.response.send_message(
                "A session vote or session is already active.",
                ephemeral=True,
            )
            return

        channel = self.get_session_channel(interaction.guild)
        if channel is None:
            await interaction.response.send_message(
                "The session channel is not configured. Check SESSION_CHANNEL_ID.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Horizon Roleplay | Session Vote",
            description=(
                "A session is being planned. Click **Vote to Join** if you "
                "would attend. Click again to remove your vote. When the vote "
                f"reaches **{REQUIRED_VOTES}**, the session information will post automatically."
            ),
            color=ORANGE,
        )
        embed.add_field(name="Votes", value=f"0/{REQUIRED_VOTES}", inline=True)
        embed.add_field(name="Status", value="🟡 Vote open", inline=True)
        embed.set_footer(text="Horizon Roleplay • Session Hosts")

        self.vote_view = SessionVoteView(self, channel)
        self.vote_message = await channel.send(
            embed=embed,
            view=self.vote_view,
        )

        await interaction.response.send_message(
            f"Session vote posted in {channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="session-force-start",
        description="Start the session without waiting for the vote threshold.",
    )
    async def session_force_start(self, interaction: discord.Interaction):
        if not await self.require_session_host(interaction):
            return

        if self.session_message is not None:
            await interaction.response.send_message(
                "A session has already started.",
                ephemeral=True,
            )
            return

        channel = self.get_session_channel(interaction.guild)
        if channel is None:
            await interaction.response.send_message(
                "The session channel is not configured.",
                ephemeral=True,
            )
            return

        vote_count = len(self.vote_view.voters) if self.vote_view else 0

        if self.vote_view:
            self.vote_view.completed = True
            for item in self.vote_view.children:
                item.disabled = True
        if self.vote_message:
            poll_embed = self.vote_message.embeds[0].copy()
            poll_embed.set_field_at(
                1,
                name="Status",
                value="🟢 Force-started by a Session Host",
                inline=True,
            )
            await self.vote_message.edit(embed=poll_embed, view=self.vote_view)

        self.vote_view = None
        await self.start_session(channel, vote_count, forced=True)
        await interaction.response.send_message(
            "The session has been force-started.",
            ephemeral=True,
        )

    @app_commands.command(
        name="session-shutdown",
        description="Cancel the session vote or close the active session.",
    )
    async def session_shutdown(self, interaction: discord.Interaction):
        if not await self.require_session_host(interaction):
            return

        changed = False

        if self.vote_view:
            self.vote_view.completed = True
            for item in self.vote_view.children:
                item.disabled = True
            if self.vote_message:
                poll_embed = self.vote_message.embeds[0].copy()
                poll_embed.set_field_at(
                    1,
                    name="Status",
                    value="🔴 Vote shut down by a Session Host",
                    inline=True,
                )
                await self.vote_message.edit(
                    embed=poll_embed,
                    view=self.vote_view,
                )
            self.vote_view = None
            changed = True

        if self.session_message:
            embeds = [embed.copy() for embed in self.session_message.embeds]
            session_embed = embeds[-1]
            session_embed.add_field(
                name="Session Status",
                value="🔴 Session shut down by a Session Host",
                inline=False,
            )
            await self.session_message.edit(embeds=embeds)
            self.session_message = None
            changed = True

        if not changed:
            await interaction.response.send_message(
                "There is no active session vote or session to shut down.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "The session vote/session has been shut down.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Sessions(bot))
