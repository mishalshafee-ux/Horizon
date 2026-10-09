import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands

import config


def blocked_user_ids():
    raw_ids = os.getenv("BOT_BLOCKED_USER_IDS", "")
    return {
        int(value.strip())
        for value in raw_ids.split(",")
        if value.strip().isdigit()
    }


class HorizonCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in blocked_user_ids():
            await interaction.response.send_message(
                "You are not allowed to use this bot's commands.",
                ephemeral=True,
            )
            return False
        return True


class HorizonBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            tree_cls=HorizonCommandTree,
        )
        self.add_check(self.blocked_user_check)

    async def blocked_user_check(self, ctx):
        if ctx.author.id in blocked_user_ids():
            await ctx.reply(
                "You are not allowed to use this bot's commands.",
                mention_author=False,
            )
            return False
        return True

    async def setup_hook(self):
        extensions = (
            "cogs.commands",
            "cogs.tickets",
            "cogs.welcome",
            "cogs.sessions",
            "cogs.verify",
            "cogs.bible",
            "cogs.erlc",
            "cogs.say",
        )

        for extension in extensions:
            await self.load_extension(extension)

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            # Remove old global copies so commands appear once in the server.
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        else:
            await self.tree.sync()

    async def update_member_count_status(self, guild=None):
        guild = guild or self.get_guild(config.GUILD_ID)
        if guild is None:
            return

        count = guild.member_count
        if count is None:
            count = len(guild.members)

        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"over {count:,} members",
            ),
        )

    async def on_ready(self):
        await self.update_member_count_status()
        print(f"Logged in as {self.user} — Horizon Roleplay bot is online.")

    async def on_member_join(self, member):
        await self.update_member_count_status(member.guild)

    async def on_member_remove(self, member):
        await self.update_member_count_status(member.guild)


async def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("Set DISCORD_TOKEN in Wispbyte environment variables.")

    async with HorizonBot() as bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
