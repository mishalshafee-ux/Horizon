import discord
from discord import app_commands
from discord.ext import commands

import config


def is_session_host(member: discord.Member) -> bool:
    return any(role.id == config.SESSION_HOST_ROLE_ID for role in member.roles)


class SessionVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.voters: set[int] = set()

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
            message = "Your join vote has been removed."
        else:
            self.voters.add(interaction.user.id)
            message = "Your join vote has been counted."

        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
        else:
            embed = discord.Embed(
                title="Horizon Roleplay | Session Vote",
                color=discord.Color.from_rgb(245, 190, 95),
            )

        vote_field = next(
            (i for i, field in enumerate(embed.fields) if field.name == "Join Votes"),
            None,
        )

        if vote_field is None:
            embed.add_field(
                name="Join Votes",
                value=str(len(self.voters)),
                inline=True,
            )
        else:
            embed.set_field_at(
                vote_field,
                name="Join Votes",
                value=str(len(self.voters)),
                inline=True,
            )

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(message, ephemeral=True)


class Sessions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_message: discord.Message | None = None
        self.session_view: SessionVoteView | None = None

    async def require_session_host(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Use this command in the Horizon Roleplay server.",
                ephemeral=True,
            )
            return False

        if not is_session_host(interaction.user):
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

        channel = interaction.guild.get_channel(config.SESSION_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "The session channel is not configured.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Horizon Roleplay | Session Vote",
            description=(
                "A session is being planned. Click **Vote to Join** if you "
                "plan to attend. Click again to remove your vote."
            ),
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.add_field(name="Server Name", value="Horizon Roleplay", inline=False)
        embed.add_field(name="Server Code", value="To be announced", inline=True)
        embed.add_field(name="Session Status", value="🟡 Vote open", inline=True)
        embed.add_field(name="Join Votes", value="0", inline=True)
        embed.set_footer(text="Horizon Roleplay • Session Hosts")

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
                "There is no active session vote to close.",
                ephemeral=True,
            )
            return

        for item in self.session_view.children:
            item.disabled = True

        embed = self.session_message.embeds[0]
        status_field = next(
            (i for i, field in enumerate(embed.fields)
             if field.name == "Session Status"),
            None,
        )

        if status_field is not None:
            embed.set_field_at(
                status_field,
                name="Session Status",
                value="🔴 Vote closed",
                inline=True,
            )

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Sessions(bot))