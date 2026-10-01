import asyncio

import discord
from discord.ext import commands

import config


class HorizonBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self):
        extensions = (
            "cogs.commands",
            "cogs.tickets",
            "cogs.welcome",
            "cogs.sessions",
        )

        for extension in extensions:
            await self.load_extension(extension)

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} — Horizon Roleplay bot is online.")


async def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("Set DISCORD_TOKEN in your .env file.")

    async with HorizonBot() as bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
