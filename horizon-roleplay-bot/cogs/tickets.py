import html
import io
import re

import discord
from discord.ext import commands

import config


TICKET_TYPES = {
    "general": {
        "label": "General Support",
        "description": "Questions, help, or general information.",
        "category_id": config.GENERAL_TICKET_CATEGORY_ID,
        "role_id": config.GENERAL_TICKET_ROLE_ID,
    },
    "management": {
        "label": "Management",
        "description": "Partnerships, community concerns, or management inquiries.",
        "category_id": config.MANAGEMENT_TICKET_CATEGORY_ID,
        "role_id": config.MANAGEMENT_TICKET_ROLE_ID,
    },
    "internal_affairs": {
        "label": "Internal Affairs",
        "description": "Staff conduct concerns or serious reports.",
        "category_id": config.IA_TICKET_CATEGORY_ID,
        "role_id": config.IA_TICKET_ROLE_ID,
    },
}


def build_transcript(messages: list[discord.Message], channel: discord.TextChannel) -> bytes:
    entries = []

    for message in messages:
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        content = html.escape(message.content or "")

        if message.embeds:
            for embed in message.embeds:
                if embed.title:
                    content += f"\n[Embed title] {html.escape(embed.title)}"
                if embed.description:
                    content += f"\n[Embed] {html.escape(embed.description)}"

        if message.attachments:
            for attachment in message.attachments:
                content += (
                    f"\n[Attachment] "
                    f'<a href="{html.escape(attachment.url, quote=True)}">'
                    f"{html.escape(attachment.filename)}</a>"
                )

        entries.append(
            f"<article><strong>{html.escape(message.author.display_name)}</strong> "
            f"<time>{timestamp}</time><pre>{content or '(no text)'}</pre></article>"
        )

    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Horizon Roleplay ticket transcript</title>
<style>
body {{ background:#202127; color:#e5e7eb; font:15px Arial,sans-serif;
       max-width:900px; margin:32px auto; padding:0 20px; }}
h1 {{ color:#f5be5f; }}
article {{ border-bottom:1px solid #3b3d46; padding:14px 0; }}
time {{ color:#9ca3af; font-size:12px; margin-left:8px; }}
pre {{ white-space:pre-wrap; font:inherit; }}
a {{ color:#79aaff; }}
</style>
</head>
<body>
<h1>Horizon Roleplay | Ticket Transcript</h1>
<p>Channel: {html.escape(channel.name)}</p>
{''.join(entries)}
</body>
</html>"""

    return page.encode("utf-8")


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket & Save Transcript",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="horizon:close_ticket",
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        channel = interaction.channel
        guild = interaction.guild

        if not isinstance(channel, discord.TextChannel) or guild is None:
            await interaction.response.send_message(
                "This ticket channel could not be found.",
                ephemeral=True,
            )
            return

        topic = channel.topic or ""
        opener_match = re.search(r"Opener ID: (\d+)", topic)
        opener_id = int(opener_match.group(1)) if opener_match else 0

        ticket_type = next(
            (
                item for item in TICKET_TYPES.values()
                if item["category_id"] == channel.category_id
            ),
            None,
        )
        staff_role_id = ticket_type["role_id"] if ticket_type else 0

        is_opener = interaction.user.id == opener_id
        is_staff = (
            interaction.user.guild_permissions.manage_channels
            or (
                isinstance(interaction.user, discord.Member)
                and any(role.id == staff_role_id for role in interaction.user.roles)
            )
        )

        if not is_opener and not is_staff:
            await interaction.response.send_message(
                "Only the ticket opener or assigned staff can close this ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        messages = [message async for message in channel.history(limit=None, oldest_first=True)]
        transcript = build_transcript(messages, channel)
        filename = f"{channel.name}-transcript.html"
        file = discord.File(io.BytesIO(transcript), filename=filename)

        log_channel_id = getattr(config, "TICKET_LOG_CHANNEL_ID", 0)
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None
        archived = False

        if isinstance(log_channel, discord.TextChannel):
            try:
                await log_channel.send(
                    content=f"Transcript for **{channel.name}** (closed by {interaction.user.mention}).",
                    file=file,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                archived = True
            except discord.HTTPException:
                pass

        if not archived and opener_id:
            try:
                opener = guild.get_member(opener_id) or await guild.fetch_member(opener_id)
                await opener.send(
                    "Here is the transcript from your Horizon Roleplay ticket.",
                    file=discord.File(io.BytesIO(transcript), filename=filename),
                )
                archived = True
            except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                pass

        if not archived:
            await interaction.followup.send(
                "I couldn't deliver the transcript. The ticket is still open. "
                "Please configure a ticket log channel or allow ticket DMs.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "Transcript saved. Closing the ticket.",
            ephemeral=True,
        )
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
            placeholder="Select a support type…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="horizon:ticket_type",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Open a ticket from inside the Horizon Roleplay server.",
                ephemeral=True,
            )
            return

        ticket_type = TICKET_TYPES[self.values[0]]
        category = guild.get_channel(ticket_type["category_id"])
        staff_role = guild.get_role(ticket_type["role_id"])

        if not isinstance(category, discord.CategoryChannel) or staff_role is None:
            await interaction.response.send_message(
                "That ticket team is not configured correctly. Please contact staff.",
                ephemeral=True,
            )
            return

        safe_name = re.sub(r"[^a-z0-9-]", "-", interaction.user.name.lower()).strip("-")
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
                f"You already have an open ticket: {existing.mention}",
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
                attach_files=True,
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
            title=f"{ticket_type['label']} Ticket",
            description=(
                f"Welcome, {interaction.user.mention}. Your ticket is private "
                f"to you and the **{staff_role.name}** team.\n\n"
                "**To help us respond quickly:**\n"
                "• Explain the issue clearly.\n"
                "• Include relevant usernames, dates, and details.\n"
                "• Attach screenshots or other evidence when useful.\n\n"
                "A team member will reply when available. Use **Close Ticket "
                "& Save Transcript** when your request is resolved."
            ),
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.set_footer(text="Horizon Roleplay • Support")

        await channel.send(
            content=staff_role.mention,
            embed=embed,
            view=CloseTicketView(),
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

        await interaction.response.send_message(
            f"Your private ticket is ready: {channel.mention}",
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

    @commands.command(name="ticket-panel")
    async def ticket_panel(self, ctx: commands.Context):
        if not ctx.guild or not ctx.author.guild_permissions.manage_guild:
            return

        embed = discord.Embed(
            title="Horizon Roleplay Support Centre",
            description=(
                "If you have a question, partnership request, or report, open a ticket "
                "below. Please provide clear details and "
                "evidence where relevant.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "## General Support\n"
                "- Questions\n"
                "- General information.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "## Management Support\n"
                "- Partnerships\n"
                "- Community concerns\n"
                "- High-ranking questions.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "## Internal Affairs Support\n"
                "- Staff conduct"
                "- Member Report"
                "- Staff Reports.\n\n"
                "Select the category that best matches your request."
            ),
            color=discord.Color.from_rgb(245, 190, 95),
        )
        embed.set_footer(text="Horizon Roleplay • Support")

        banner_url = getattr(config, "HORIZON_BANNER_URL", "")
        if banner_url:
            embed.set_image(url=banner_url)

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        await ctx.send(embed=embed, view=TicketPanelView())


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))