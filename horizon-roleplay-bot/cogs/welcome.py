import discord
from discord.ext import commands

import config


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        information_channel_id = getattr(config, "INFORMATION_CHANNEL_ID", 0)
        information_channel = member.guild.get_channel(information_channel_id)

        if isinstance(information_channel, discord.TextChannel):
            next_steps = (
                f"Please review {information_channel.mention} for server "
                "information and guidance before joining a session."
            )
        else:
            next_steps = (
                "Please review the server information and rules before "
                "joining a session."
            )

        embed = discord.Embed(
            title=" Welcome to Horizon Roleplay! ",
            description=(
                f"Thank you for joining **Horizon Roleplay**, {member.mention}!\n\n"
                f" {next_steps}\n\n"
                "We’re glad you’re here. Enjoy your time with the community!"
            ),
            color=discord.Color.from_rgb(245, 159, 112),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(
            text="Horizon Roleplay",
            icon_url=member.guild.icon.url if member.guild.icon else None,
        )

        await channel.send(
            content=member.mention,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))