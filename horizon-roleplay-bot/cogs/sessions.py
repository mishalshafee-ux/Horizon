import discord
from discord import app_commands
from discord.ext import commands

import config
from .erlc import ERLCAPIError, get_server_data


class SessionVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.voters = set()

    @discord.ui.button(
        label="Vote to Join",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="horizon:session_vote_to_join",
    )
    async def vote_to_join(self, interaction, button):
        if interaction.user.id in self.voters:
            self.voters.remove(interaction.user.id)
            reply = "Your join vote has been removed."
        else:
            self.voters.add(interaction.user.id)
            reply = "Your join vote has been counted."

        embed = interaction.message.embeds[0]
        field_index = next(
            (i for i, field in enumerate(embed.fields) if field.name == "Join Votes"),
            None,
        )

        if field_index is None:
            embed.add_field(
                name="Join Votes",
                value=str(len(self.voters)),
                inline=True,
            )
        else:
            embed.set_field_at(
                field_index,
                name="Join Votes",
                value=str(len(self.voters)),
                inline=True,
            )

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(reply, ephemeral=True)


class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_message = None
        self.session_view = None

    async def require_session_host(self, interaction):
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
        description="Post a session announcement with a join vote.",
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
                "The session channel is not configured.",
                ephemeral=True,
            )
            return

        try:
            data = await get_server_data()
            player_count = (
                f"{data.get('CurrentPlayers', 0)}/"
                f"{data.get('MaxPlayers', '?')}"
            )
            server_code = data.get("JoinKey") or "Horrp"
            queue_count = len(data.get("Queue") or [])
            staff_count = len((data.get("Staff") or {}).get("Mods") or {})
        except ERLCAPIError:
            player_count = "Unavailable"
            server_code = "Horrp"
            queue_count = "Unavailable"
            staff_count = "Unavailable"

        embed = discord.Embed(
            title="Horizon Roleplay | Session Information",
            description=(
                "> A session is being planned. Click **Vote to Join** if you "
                "> plan to attend. Click again to remove your vote."
            ),
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.add_field(
            name="Server Details",
            value=(
                "**> Server Name:** Horizon Roleplay\n"
                
                
                f"**> Server Code:** `{server_code}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Live Server Activity",
            value=(
                f"**> In-game Players:** {player_count}\n"
                
                f"**> Currently Moderating:** {staff_count}\n"
                
                f"**> In-Queue Players:** {queue_count}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Session Status",
            value="🟡 Vote open",
            inline=True,
        )
        embed.add_field(name="Join Votes", value="0", inline=True)
        embed.set_footer(text="Horizon Roleplay • Hosted by Session Hosts")

        banner_url = getattr(config, "HORIZON_BANNER_URL", "")
        if banner_url:
            embed.set_image(url=banner_url)

        self.session_view = SessionVoteView()
        self.session_message = await channel.send(
            embed=embed,
            view=self.session_view,
        )

        await interaction.response.send_message(
            f"Session vote posted in {channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="session-end",
        description="Close the current session vote.",
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

        embed = self.session_message.embeds[0]
        for index, field in enumerate(embed.fields):
            if field.name == "Session Status":
                embed.set_field_at(
                    index,
                    name="Session Status",
                    value="🔴 Vote closed",
                    inline=True,
                )
                break

        await self.session_message.edit(
            embed=embed,
            view=self.session_view,
        )

        self.session_message = None
        self.session_view = None

        await interaction.response.send_message(
            "The session vote is closed.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Sessions(bot))
