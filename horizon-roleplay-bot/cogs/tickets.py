import discord
from discord import app_commands
from discord.ext import commands

import config


TICKET_TYPES = {
    "general": {
        "label": "General Support",
        "description": "Questions or general assistance.",
        "category_id": config.GENERAL_TICKET_CATEGORY_ID,
        "role_id": config.GENERAL_TICKET_ROLE_ID,
    },
    "management": {
        "label": "Management",
        "description": "Management questions or concerns.",
        "category_id": config.MANAGEMENT_TICKET_CATEGORY_ID,
        "role_id": config.MANAGEMENT_TICKET_ROLE_ID,
    },
    "internal_affairs": {
        "label": "Internal Affairs",
        "description": "Staff conduct or serious player reports.",
        "category_id": config.IA_TICKET_CATEGORY_ID,
        "role_id": config.IA_TICKET_ROLE_ID,
    },
}


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="horizon:close_ticket",
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "This ticket channel could not be found.",
                ephemeral=True,
            )
            return

        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "You need Manage Channels permission to close this ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Closing this ticket…", ephemeral=True)
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=item["label"],
                value=key,
                description=item["description"],
            )
            for key, item in TICKET_TYPES.items()
        ]

        super().__init__(
            placeholder="Select a support category…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="horizon:ticket_type",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Tickets can only be opened in a server.",
                ephemeral=True,
            )
            return

        ticket_type = TICKET_TYPES[self.values[0]]
        category = guild.get_channel(ticket_type["category_id"])
        staff_role = guild.get_role(ticket_type["role_id"])

        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                f"The {ticket_type['label']} category is not configured. "
                "Ask a server administrator to check its category ID.",
                ephemeral=True,
            )
            return

        if staff_role is None:
            await interaction.response.send_message(
                f"The {ticket_type['label']} staff role is not configured. "
                "Ask a server administrator to check its role ID.",
                ephemeral=True,
            )
            return

        safe_name = "".join(
            character.lower() if character.isalnum() else "-"
            for character in interaction.user.name
        ).strip("-")
        channel_name = f"ticket-{safe_name[:40]}"

        existing = next(
            (
                channel for channel in category.text_channels
                if channel.topic
                and f"Opener ID: {interaction.user.id}" in channel.topic
            ),
            None,
        )
        if existing:
            await interaction.response.send_message(
                f"You already have a ticket open: {existing.mention}",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=(
                f"Horizon Roleplay | {ticket_type['label']} | "
                f"Opener ID: {interaction.user.id}"
            ),
        )

        embed = discord.Embed(
            title=ticket_type["label"],
            description=(
                f"Hi {interaction.user.mention}! Please describe what you need "
                "help with. The appropriate team has been notified."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Horizon Roleplay Support")

        await channel.send(
            content=staff_role.mention,
            embed=embed,
            view=CloseTicketView(),
        )
        await interaction.response.send_message(
            f"Your ticket is open: {channel.mention}",
            ephemeral=True,
        )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(TicketPanelView())
        bot.add_view(CloseTicketView())

    @app_commands.command(
        name="ticket-panel",
        description="Post the Horizon Roleplay support panel.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Horizon Roleplay Support",
            description=(
                "Choose the team that best fits your request. "
                "Your ticket will be visible to you and that team's staff."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="General Support",
            value="Questions or general assistance.",
            inline=False,
        )
        embed.add_field(
            name="Management",
            value="Management questions or concerns.",
            inline=False,
        )
        embed.add_field(
            name="Internal Affairs",
            value="Staff conduct or serious player reports.",
            inline=False,
        )
        embed.set_footer(text="Horizon Roleplay")

        await interaction.response.send_message(
            embed=embed,
            view=TicketPanelView(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
