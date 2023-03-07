import discord
from discord.ext import commands, tasks

from blagues_api import BlaguesAPI, BlagueType

import os
import re

from dotenv import load_dotenv, find_dotenv

import asyncio
import aiohttp

import platform

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv(find_dotenv())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_REPO_URL = os.getenv("GITLAB_REPO_URL")
GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_API_URL = f'https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests' \
                 f'?state=opened' \
                 f'&per_page=250' \
                 f'&private_token={GITLAB_TOKEN}'

JIRA_URL = os.getenv("JIRA_URL")

IS_DEBUG_MODE = eval(os.getenv("IS_DEBUG_MODE", "False"))

BLAGUES_API_TOKEN = os.getenv("BLAGUES_API_TOKEN")
blagues = BlaguesAPI(BLAGUES_API_TOKEN)

command_prefix = ">" if IS_DEBUG_MODE else "$"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

previous_last_merge_request_id = None


@bot.command(name="ticket", aliases=["t", "tickets", "jira", "j"])
async def display_jira_tickets(ctx, *tickets):
    """
    Displays selected Jira tickets
    """

    embed = discord.Embed(title="Tickets Jira", color=0x0052cc)

    if not tickets:
        embed.add_field(name="", value="No ticket provided", inline=False)
        await ctx.send(embed=embed)
    elif all(not ticket_id.isdigit() for ticket_id in tickets):
        embed.add_field(name="", value="No ticket numbers found", inline=False)
        await ctx.send(embed=embed)


@bot.command(name="loop")
async def loop_manager(ctx, command=None):
    """
    Manages the loop that check for new merge requests
    """
    if command is None:
        await ctx.send("No command provided\nAvailable commands: -r restart, -s stop")
    elif command in {"-r", "restart"}:
        await ctx.send(f"Loop restarted")
        last_merge_request_checker.start()
    elif command in {"-s", "stop"}:
        await ctx.send(f"Loop stopped")
        last_merge_request_checker.cancel()
    else:
        await ctx.send("Unknown command\nAvailable commands: -r restart, -s stop")


@bot.command(name="joke", aliases=["blague"])
async def display_random_joke(ctx, kind="global"):
    """
    Displays a random joke
    """
    if kind not in {t.value for t in BlagueType}:
        joke = await blagues.random(disallow=[BlagueType.LIMIT, BlagueType.BEAUF, BlagueType.DARK])
        new_joke = await ctx.send(joke.joke)
    else:
        joke = await blagues.random_categorized(kind)
        new_joke = await ctx.send(joke.joke)

    await asyncio.sleep(2)
    await new_joke.edit(content=f"{joke.joke}\n||{joke.answer}||")


@bot.listen()
async def on_ready():
    """Start the tasks loop when the bot is ready"""
    print(f"{bot.user} is connected to the following guilds:")
    for guild in bot.guilds:
        print(f"\t{guild.name}(id: {guild.id})")

    if not last_merge_request_checker.is_running() and not IS_DEBUG_MODE:
        print("Starting last_merge_request_checker task loop...")
        last_merge_request_checker.start()


@bot.command(name="git", aliases=["g", "gitlab", "mr", "merge_request", "merge_requests", "mrs"])
async def list_merge_requests(ctx, *params):
    """
    List all current merge requests
    """
    params = list(params)

    async with aiohttp.ClientSession() as session:
        async with session.get(GITLAB_API_URL) as resp:
            global previous_last_merge_request_id
            if resp.status != 200:
                print(f"{resp.status} Error while fetching data from Gitlab")
                return

            unconcerned_users = {"Cafeine42", "BonaventureEleonore", "guillaumeharari", "AlexSarrazin"}
            merge_requests = await resp.json()
            merge_requests = sorted(
                (mr for mr in merge_requests if mr["author"]["username"] not in unconcerned_users),
                key=lambda mr: mr["iid"])

            if params:
                if "conflicts" in params:
                    params.remove("conflicts")
                    merge_requests = [mr for mr in merge_requests if mr["has_conflicts"]]

                merge_requests = [mr for mr in merge_requests if (mr["target_branch"] in params if params else True)]

            sorted_merge_requests = {}
            for mr in merge_requests:
                if mr["author"]["username"] not in sorted_merge_requests:
                    sorted_merge_requests[mr["author"]["username"]] = []
                sorted_merge_requests[mr["author"]["username"]].append(mr)

            for mr_user, mrs in sorted_merge_requests.items():
                embed = discord.Embed(title=f"{mr_user} (total: {len(mrs)})",
                                      color=0x0052cc)

                for mr in mrs:
                    mrs_list = f"⦁ [{mr['iid']}]({mr['web_url']}) -> " \
                               f"[`{mr['target_branch']}`]({GITLAB_REPO_URL}/tree/{mr['target_branch']})"
                    embed.add_field(name=f"{mr['title']}",
                                    value=mrs_list,
                                    inline=False)

                await ctx.send(embed=embed)


@tasks.loop(seconds=8)
async def last_merge_request_checker():
    """Check for new merge requests"""
    async with aiohttp.ClientSession() as session:
        async with session.get(GITLAB_API_URL) as resp:
            global previous_last_merge_request_id
            if resp.status != 200:
                print(f"{resp.status} Error while fetching data from Gitlab")
                return
            merge_requests = await resp.json()

            last_merge_request = max(
                (mr for mr in merge_requests if mr["author"]["username"] not in {"Cafeine42", "BonaventureEleonore"}),
                key=lambda mr: mr["iid"])

            if previous_last_merge_request_id is None:
                previous_last_merge_request_id = last_merge_request["id"]
                return

            if last_merge_request["id"] <= previous_last_merge_request_id:
                return

            previous_last_merge_request_id = last_merge_request["id"]

            side_color = discord.Color.red() if last_merge_request["has_conflicts"] else discord.Color.green()
            mr_author = last_merge_request["author"]["name"].replace("-", " ").replace("_", " ")
            mr_author = re.sub(r"([a-z])([A-Z])", r"\1 \2", mr_author).replace("  ", " ").title().strip()

            embed = discord.Embed(title=mr_author, color=side_color)
            embed.set_thumbnail(url=last_merge_request["author"]["avatar_url"])
            embed.add_field(name="",
                            value=last_merge_request["title"],
                            inline=False)

            mr_jira_id = re.search(r"^BOBY-(\d+)", last_merge_request['source_branch'])
            if mr_jira_id:
                mr_jira_id = mr_jira_id.groups()[0]
                embed.add_field(name="Lien Jira",
                                value=f"[BOBY-{mr_jira_id}]({JIRA_URL}-{mr_jira_id})",
                                inline=True)

            if last_merge_request['target_branch']:
                embed.add_field(name="Branche cible",
                                value=f"[`{last_merge_request['target_branch']}`]({GITLAB_REPO_URL}/tree/{last_merge_request['target_branch']})",
                                inline=True)

            if last_merge_request['labels']:
                embed.add_field(name="Labels",
                                value=' • '.join(label for label in last_merge_request['labels']),
                                inline=True)

            if last_merge_request['has_conflicts']:
                embed.add_field(
                    name=f"⚠️ [Merge Conflict]({GITLAB_REPO_URL}/merge_requests/{last_merge_request['iid']}/conflicts) ⚠️",
                    value="",
                    inline=True)

            channel = bot.get_guild(GUILD_ID).get_channel(CHANNEL_ID)
            await channel.send(embed=embed,
                               content=f"MR {GITLAB_REPO_URL}/merge_requests/{last_merge_request['iid']}")


@bot.listen()
async def on_message(message):
    """
    Check for Jira and Git tickets in messages
    """
    if message.author.id == self.user.id:
        return

    jira_commands = [display_jira_tickets.name] + display_jira_tickets.aliases
    jira_message_checker = "\\" + command_prefix + "(?:" + "|".join(jira_commands) + r") ([\d ]+)(?=\D|$)"
    jira_tickets = re.findall(jira_message_checker, message.content)
    if jira_tickets:
        embed = discord.Embed(title="Tickets Jira", color=0x0052cc)
        for group_num, tickets_group in enumerate(jira_tickets, 1):
            tickets_group = tickets_group.strip().split(" ")
            unique_tickets = list(dict.fromkeys(tickets_group))

            embed.add_field(name=f"Groupe {group_num}" if len(jira_tickets) > 1 else "",
                            value="".join(
                                f"⦁ [BOBY-{ticket_id}]({JIRA_URL}-{ticket_id})\n" for ticket_id in unique_tickets if
                                ticket_id.isdigit()),
                            inline=True)

        channel = bot.get_guild(message.guild.id).get_channel(message.channel.id)
        await channel.send(embed=embed)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
