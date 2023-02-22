import discord
from discord.ext import commands, tasks

from gitlab import Gitlab

import os
import re

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 310945319372455936
CHANNEL_ID = 1077880800218972201

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_REPO_ID = os.getenv("GITLAB_REPO_ID")
GITLAB_REPO_URL = os.getenv("GITLAB_REPO_URL")

JIRA_URL = os.getenv("JIRA_URL")

print(GUILD_ID, CHANNEL_ID)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=">", intents=intents)


def lb(text: str) -> str:
    """Add line break to the end of the text"""
    return text + "\n"


@bot.command()
async def helper(ctx):
    return_text = lb("Available commands:")
    available_commands = {"ticket": "ticket [-d, --details, details] <ticket_id>...",
                          "helper": "helper",
                          "loop": "loop [-r, --restart, restart] [-s, --stop, stop]"}

    for command, detail in available_commands.items():
        return_text += lb(f"`{command}` - {detail}")

    await ctx.send(return_text)


@bot.command()
async def ticket(ctx, *tickets):
    tickets = tuple(set(tickets))

    embed = discord.Embed(
        title="Jira Tickets",
        color=0x0052cc)

    if tickets:
        if any(p in {"-d", "--details", "details"} for p in tickets):
            print("details")

        for ticket_id in tickets:
            if ticket_id.isdigit():
                embed.add_field(name="", value=f"[BOBY-{ticket_id}]({JIRA_URL}-{ticket_id})", inline=False)
    else:
        embed.add_field(name="", value=f"No tickets provided", inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def loop(ctx, command=None):
    if command is None:
        await ctx.send(merge_request_checker.get_task())
    elif command in {"-i", "--info", "info"}:
        await ctx.send("2")
    elif command in {"-r", "--restart", "restart"}:
        await ctx.send(f"Loop restarted")
        merge_request_checker.start()
    elif command in {"-s", "--stop", "stop"}:
        await ctx.send(f"Loop stopped")
        merge_request_checker.cancel()
    else:
        await ctx.send("Unknown command\nAvailable commands: -r --restart restart, -s --stop stop, -i --info info")


@bot.listen()
async def on_ready():
    # merge_request_checker.start()
    pass


@tasks.loop(seconds=5)
async def merge_request_checker():
    gl_repo = Gitlab(private_token=GITLAB_TOKEN).groups.get(GITLAB_REPO_ID)
    merge_requests = gl_repo.mergerequests.list(state="opened", get_all=True)
    last_merge_request = max(
        (mr for mr in merge_requests if mr.author["username"] not in {"Cafeine42", "BonaventureEleonore"}),
        key=lambda mr: mr.iid)

    channel = bot.get_guild(GUILD_ID).get_channel(CHANNEL_ID)
    await channel.send(last_merge_request)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
