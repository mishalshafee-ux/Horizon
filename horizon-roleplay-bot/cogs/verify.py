import os
import re
import secrets
import string

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


COLOR = 0xEAC5FD
VERIFY_ROLE_ID = int(os.getenv("VERIFY_ROLE_ID", "0") or 0)
UNVERIFIED_ROLE_ID = int(os.getenv("UNVERIFIED_ROLE_ID", "0") or 0)

# Temporary in-memory challenges. A bot restart clears unfinished verifications.
PENDING_VERIFICATIONS: dict[int, dict] = {}


def make_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "HORIZON-" + "".join(secrets.choice(alphabet) for _ in range(6))


def normalize_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


async def get_roblox_user(username: str) -> dict | None:
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {
        "usernames": [username],
        "excludeBannedUsers": False,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                users = data.get("data", [])
                return users[0] if users else None
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return None


async def get_roblox_bio(user_id: int) -> str:
    url = f"https://users.roblox.com/v1/users/{user_id}"

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return ""

                data = await response.json()
                return data.get("description", "")
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return ""


class ConfirmVerifyView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600)
        self.user_id = user_id

    @discord.ui.button(
        label="I Added The Code",
        style=discord.ButtonStyle.success,
        custom_id="horizon:confirm_roblox_verify",
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This verification button belongs to another member.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        data = PENDING_VERIFICATIONS.get(interaction.user.id)
        if not data:
            await interaction.followup.send(
                "Your verification session expired. Start again with the "
                "Verify button.",
                ephemeral=True,
            )
            return

        bio = await get_roblox_bio(data["roblox_id"])
        if normalize_text(data["code"]) not in normalize_text(bio):
            await interaction.followup.send(
                "I couldn't find the code in that Roblox profile's About/Bio. "
                "Check that it was saved, wait a little for Roblox to update, "
                "then try again.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "Run verification from inside the Horizon Roleplay server.",
                ephemeral=True,
            )
            return

        verified_role = guild.get_role(VERIFY_ROLE_ID)
        unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

        if verified_role is None:
            await interaction.followup.send(
                "The verified role isn't configured. Please contact staff.",
                ephemeral=True,
            )
            return

        try:
            await interaction.user.add_roles(
                verified_role,
                reason="Roblox account ownership verified.",
            )

            if unverified_role and unverified_role in interaction.user.roles:
                await interaction.user.remove_roles(
                    unverified_role,
                    reason="Roblox account ownership verified.",
                )
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't update your roles. Please ask staff to check the "
                "bot's Manage Roles permission and role position.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "Discord couldn't update your roles just now. Please try again "
                "or contact staff.",
                ephemeral=True,
            )
            return

        # Keep the existing nickname and append the linked Roblox username.
        nickname = f"{interaction.user.display_name} (@{data['roblox_username']})"
        try:
            await interaction.user.edit(
                nick=nickname[:32],
                reason="Roblox account verified.",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        PENDING_VERIFICATIONS.pop(interaction.user.id, None)
        await interaction.followup.send(
            f"✅ Verified as **{data['roblox_username']}**. "
            f"You received {verified_role.mention}.",
            ephemeral=True,
        )


class VerifyModal(discord.ui.Modal, title="Verify Roblox Account"):
    roblox_username = discord.ui.TextInput(
        label="Roblox Username",
        placeholder="Enter your Roblox username",
        required=True,
        max_length=32,
    )

    async def on_submit(self, interaction: discord.Interaction):
        username = str(self.roblox_username.value).strip()

        await interaction.response.defer(ephemeral=True, thinking=True)
        roblox_user = await get_roblox_user(username)

        if not roblox_user:
            await interaction.followup.send(
                "I couldn't find that Roblox username. Check the spelling and "
                "try again.",
                ephemeral=True,
            )
            return

        code = make_code()
        PENDING_VERIFICATIONS[interaction.user.id] = {
            "code": code,
            "roblox_id": roblox_user["id"],
            "roblox_username": roblox_user["name"],
        }

        await interaction.followup.send(
            f"To verify **{roblox_user['name']}**, add this code to your "
            f"Roblox profile About/Bio:\n\n`{code}`\n\n"
            "After saving it, wait briefly and click **I Added The Code**. "
            "You can remove the code after verification.",
            view=ConfirmVerifyView(interaction.user.id),
            ephemeral=True,
        )


class VerifyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        custom_id="horizon:open_verify_modal",
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(VerifyModal())


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(VerifyPanelView())

    @app_commands.command(
        name="verify-panel",
        description="Post the Horizon Roleplay verification panel.",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def verify_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Horizon Roleplay Verification",
            description=(
                "Verify your Roblox account to receive access to the server.\n\n"
                "**How it works**\n"
                "> 1. Click **Verify** and enter your Roblox username.\n"
                "> 2. Add the one-time code to your Roblox profile About/Bio.\n"
                "> 3. Click **I Added The Code**.\n\n"
                "Once the code is confirmed, the bot gives you the verified "
                "role and removes the unverified role. You can remove the "
                "code from your bio afterward."
            ),
            color=COLOR,
        )
        embed.set_footer(text="Horizon Roleplay Verification")

        await interaction.response.send_message(
            embed=embed,
            view=VerifyPanelView(),
        )


    @commands.command(name="verifypanel", aliases=["verify-panel"])
    @commands.has_permissions(manage_roles=True)
    async def verify_panel_prefix(self, ctx):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title="Horizon Roleplay Verification",
            description=(
                "Verify your Roblox account to receive access to the server.\n\n"
                "**How it works**\n"
                "> 1. Click **Verify** and enter your Roblox username.\n"
                "> 2. Add the one-time code to your Roblox profile About/Bio.\n"
                "> 3. Click **I Added The Code**.\n\n"
                "After verification, you’ll receive the verified role."
            ),
            color=COLOR,
        )
        embed.set_footer(text="Horizon Roleplay Verification")
        await ctx.send(embed=embed, view=VerifyPanelView())

async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
