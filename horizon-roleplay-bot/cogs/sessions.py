import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from .erlc import ERLCAPIError, get_server_data


class SessionVoteView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.voters = set()

    @discord.ui.button(
        label="Vote to Join",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="horizon:session_vote_to_join",
    )
    async def vote_to_join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id in self.voters:
            self.voters.remove(interaction.user.id)
            reply = "Your join vote has been removed."
        else:
            self.voters.add(interaction.user.id)
            reply = "Your join vote has been counted."

        info_embed = interaction.message.embeds[-1]
        for index, field in enumerate(info_embed.fields):
            if field.name == "Join Votes":
                info_embed.set_field_at(
                    index,
                    name="Join Votes",
                    value=str(len(self.voters)),
                    inline=True,
                )
                break

        await interaction.response.edit_message(
            embeds=[embed.copy() for embed in interaction.message.embeds[:-1]]
            + [info_embed],
            view=self,
        )
        await interaction.followup.send(reply, ephemeral=True)

    @discord.ui.button(
        label="Session Notification",
        style=discord.ButtonStyle.secondary,
        emoji="🔔",
        custom_id="horizon:session_notification",
    )
    async def session_notification(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        user_id = interaction.user.id

        if user_id in self.cog.notification_subscribers:
            self.cog.notification_subscribers.remove(user_id)
            reply = "Session notifications are turned off for you."
        else:
            self.cog.notification_subscribers.add(user_id)
            reply = "You’ll be notified when a session vote is posted."

        await interaction.response.send_message(reply, ephemeral=True)


class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_message = None
        self.session_view = None
        self.notification_subscribers = set()

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

    @app_commands.command(
        name="session-start",
        description="Post a Horizon Roleplay session vote.",
    )
    async def session_start(self, interaction: discord.Interaction):
        if not await self.require_session_host(interaction):
            return

        if self.session_message is not None:
            await interaction.response.send_message(
                "There is already an open session vote.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(config.SESSION_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "The session channel is not configured. Check SESSION_CHANNEL_ID.",
                ephemeral=True,
            )
            return

        try:
            data = await get_server_data()
            player_count = (
                f"{data.get('CurrentPlayers', 0)}/"
                f"{data.get('MaxPlayers', '?')}"
            )
            server_code = data.get("JoinKey") or config.SERVER_CODE
            queue_count = len(data.get("Queue") or [])
            staff_data = data.get("Staff") or {}
            staff_count = len(staff_data.get("Mods") or [])
        except ERLCAPIError:
            player_count = "Unavailable"
            server_code = config.SERVER_CODE
            queue_count = "Unavailable"
            staff_count = "Unavailable"

        now = int(time.time())
        rules_text = (
            f"[Horizon Roleplay game rules]({config.GAME_RULES_URL})"
            if config.GAME_RULES_URL
            else "Horizon Roleplay game rules"
        )

        info_embed = discord.Embed(
            title="Session Information",
            description=(
                "> Sessions are hosted by our **Session Hosts** and take place "
                "when staff are available. Vote below if you plan to attend."
            ),
            color=config.EMBED_COLOR,
        )
        info_embed.add_field(
            name="Server Details",
            value=(
                f"**Server Name:** `{config.SERVER_NAME}`\n"
                f"**Server Code:** `{server_code}`"
            ),
            inline=False,
        )
        info_embed.add_field(
            name="Live Server Activity",
            value=(
                f"**In-game Players:** `{player_count}`\n"
                f"**Currently Moderating:** `{staff_count}`\n"
                f"**In-Queue Players:** `{queue_count}`"
            ),
            inline=False,
        )
        info_embed.add_field(
            name="Last Updated",
            value=f"<t:{now}:R>",
            inline=False,
        )
        info_embed.add_field(
            name="Session Status",
            value="🟡 Vote open",
            inline=True,
        )
        info_embed.add_field(
            name="Join Votes",
            value="0",
            inline=True,
        )
        info_embed.add_field(
            name="Before Joining",
            value=f"Please review the {rules_text} before joining.",
            inline=False,
        )
        info_embed.set_footer(
            text="Horizon Roleplay • Hosted by Session Hosts"
        )

        embeds = []
        if config.SESSION_BANNER_URL:
            banner_embed = discord.Embed(color=config.EMBED_COLOR)
            banner_embed.set_image(url=config.SESSION_BANNER_URL)
            embeds.append(banner_embed)
        embeds.append(info_embed)

        self.session_view = SessionVoteView(self)

        subscribers = sorted(self.notification_subscribers)
        notification_text = (
            " ".join(f"<@{user_id}>" for user_id in subscribers)
            if subscribers
            else None
        )

        self.session_message = await channel.send(
            content=notification_text,
            embeds=embeds,
            view=self.session_view,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

        await interaction.response.send_message(
            f"Session vote posted in {channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="session-end",
        description="Close the current Horizon Roleplay session vote.",
    )
    async def session_end(self, interaction: discord.Interaction):
        if not await self.require_session_host(interaction):
            return

        if self.session_message is None or self.session_view is None:
            await interaction.response.send_message(
                "There is no open session vote to close.",
                ephemeral=True,
            )
            return

        for item in self.session_view.children:
            item.disabled = True

        embeds = [embed.copy() for embed in self.session_message.embeds]
        info_embed = embeds[-1]

        for index, field in enumerate(info_embed.fields):
            if field.name == "Session Status":
                info_embed.set_field_at(
                    index,
                    name="Session Status",
                    value="🔴 Vote closed",
                    inline=True,
                )
                break

        await self.session_message.edit(embeds=embeds, view=self.session_view)
        self.session_message = None
        self.session_view = None

        await interaction.response.send_message(
            "The session vote is closed.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Sessions(bot))
