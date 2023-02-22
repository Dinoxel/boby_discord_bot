import discord
from discord.ext import commands, tasks

from blagues_api import BlaguesAPI, BlagueType

from gitlab import Gitlab

import os
import re

from dotenv import load_dotenv, find_dotenv

# Ajouter Bad joke avec Question et réponse aléatoire sur website


load_dotenv(find_dotenv())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_REPO_ID = os.getenv("GITLAB_REPO_ID")
GITLAB_REPO_URL = os.getenv("GITLAB_REPO_URL")

JIRA_URL = os.getenv("JIRA_URL")

BLAGUES_API_TOKEN = os.getenv("BLAGUES_API_TOKEN")
blagues = BlaguesAPI(BLAGUES_API_TOKEN)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)

previous_last_merge_request = None


@bot.command()
async def helper(ctx):
    """Display all available commands"""
    return_text = "Available commands:\n"
    available_commands = {"ticket": "ticket [-d, --details, details] <ticket_id>...",
                          "helper": "helper",
                          "loop": "loop [-r, --restart, restart] [-s, --stop, stop]"}

    for command, detail in available_commands.items():
        return_text += f"`{command}` - {detail}\n"

    await ctx.send(return_text)


@bot.command()
async def ticket(ctx, *tickets):
    """Display Jira tickets"""
    tickets = list(dict.fromkeys(tickets))
    embed = discord.Embed(title="Jira Tickets", color=0x0052cc)

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
    """Manage the loop that check for new merge requests"""
    if command is None:
        await ctx.send(last_merge_request_checker.get_task())
    elif command in {"-i", "--info", "info"}:
        await ctx.send("2")
    elif command in {"-r", "--restart", "restart"}:
        await ctx.send(f"Loop restarted")
        last_merge_request_checker.start()
    elif command in {"-s", "--stop", "stop"}:
        await ctx.send(f"Loop stopped")
        last_merge_request_checker.cancel()
    else:
        await ctx.send("Unknown command\nAvailable commands: -r --restart restart, -s --stop stop, -i --info info")


@bot.command()
async def blague(ctx, kind=None):
    """Display a random joke"""
    if kind is None or kind not in {t.value for t in BlagueType}:
        joke = await blagues.random(disallow=[BlagueType.LIMIT, BlagueType.BEAUF, BlagueType.DARK])
        await ctx.send(joke.joke)

    else:
        joke = await blagues.random_categorized(kind)
        await ctx.send(joke.joke)

    sleep(2)
    await ctx.send(joke.answer)


@bot.listen()
async def on_ready():
    """Start the tasks loop when the bot is ready"""
    last_merge_request_checker.start()


@tasks.loop(seconds=6)
async def last_merge_request_checker():
    """Check for new merge requests"""

    global previous_last_merge_request

    gl_repo = Gitlab(private_token=GITLAB_TOKEN).groups.get(GITLAB_REPO_ID)
    merge_requests = gl_repo.mergerequests.list(state="opened", get_all=True)
    last_merge_request = max(
        (mr for mr in merge_requests if mr.author["username"] not in {"Cafeine42", "BonaventureEleonore"}),
        key=lambda mr: mr.iid)

    if previous_last_merge_request is None:
        previous_last_merge_request = last_merge_request.id
        return

    if last_merge_request.id <= previous_last_merge_request:
        return
    previous_last_merge_request = last_merge_request.id

    channel = bot.get_guild(GUILD_ID).get_channel(CHANNEL_ID)

    side_color = discord.Color.red() if last_merge_request.has_conflicts else discord.Color.green()
    mr_author = last_merge_request.author["name"].replace("-", " ").replace("_", " ")
    mr_author = re.sub(r"(\w)([A-Z])", r"\1 \2", mr_author).replace("  ", " ").title().strip()
    embed = discord.Embed(title=mr_author, color=side_color)

    mr_jira_id = re.search(r"^BOBY-(\d+)", last_merge_request.source_branch).groups()[0]

    embed.set_thumbnail(url=last_merge_request.author["avatar_url"])
    embed.add_field(name="", value=last_merge_request.title, inline=False)

    embed.add_field(name="Lien Jira", value=f"[BOBY-{mr_jira_id}]({JIRA_URL}-{mr_jira_id})", inline=True)

    if last_merge_request.labels:
        embed.add_field(name="Labels", value=' • '.join(label for label in last_merge_request.labels), inline=True)

    if last_merge_request.has_conflicts:
        embed.add_field(name="⚠️ Merge Conflicts ⚠️", value="", inline=True)

    await channel.send(embed=embed, content=f"MR {GITLAB_REPO_URL}/{last_merge_request.iid}")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
