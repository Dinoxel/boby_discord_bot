import discord
from discord.ext import commands, tasks
# import yt_dlp as youtube_dl

from blagues_api import BlaguesAPI, BlagueType

import os
import re
from functools import reduce

from dotenv import load_dotenv, find_dotenv

import asyncio
import aiohttp
import requests

from templates.mysql_connector import MysqlConnection
import pandas as pd

from typing import Union

import platform

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv(find_dotenv())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DISCORD_ADMIN_ROLE_ID = int(os.getenv("DISCORD_ADMIN_ROLE_ID"))

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_GROUP_NAME = os.getenv("GITLAB_GROUP_NAME")
GITLAB_PROJECT_NAME = os.getenv("GITLAB_PROJECT_NAME")
GITLAB_REPO_URL = f"https://gitlab.com/{GITLAB_GROUP_NAME}/{GITLAB_PROJECT_NAME}/-"

GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_API_URL = f'https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests' \
                 f'?state=opened' \
                 f'&per_page=250' \
                 f'&private_token={GITLAB_TOKEN}'

JIRA_MAIL = os.getenv("JIRA_MAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
JIRA_KEY = os.getenv("JIRA_KEY")
JIRA_OLD_KEY = os.getenv("JIRA_OLD_KEY")
JIRA_APP_NAME = os.getenv("JIRA_APP_NAME")

JIRA_URL = f"https://{JIRA_APP_NAME}.atlassian.net/browse/"
JIRA_API_URL = f"https://{JIRA_APP_NAME}.atlassian.net/rest/api/3/search?jql=PROJECT = {JIRA_KEY} AND KEY IN"
JIRA_AUTH = aiohttp.BasicAuth(JIRA_MAIL, JIRA_TOKEN)
JIRA_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_WORKFLOW = os.environ.get("GITHUB_REPO_WORKFLOW")
GITHUB_REPO_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_WORKFLOW}"
GITHUB_WORKFLOW_HEADERS = {"Authorization": "Bearer " + GITHUB_TOKEN, "Accept": "application/vnd.github.v3+json"}
GITHUB_WORKFLOW_EVENT_QA = os.environ.get("GITHUB_WORKFLOW_EVENT_QA")
GITHUB_WORKFLOW_EVENT_SALES = os.environ.get("GITHUB_WORKFLOW_EVENT_SALES")

IS_DEBUG_MODE = eval(os.getenv("IS_DEBUG_MODE", "False"))

BLAGUES_API_TOKEN = os.getenv("BLAGUES_API_TOKEN")
blagues = BlaguesAPI(BLAGUES_API_TOKEN)

command_prefix = "$>" if IS_DEBUG_MODE else "$"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

previous_last_merge_request_id = None
voice_client = None
last_music = None
last_music_url = None

gitlab_excluded_users = {"Cafeine42", "BonaventureEleonore", "guillaumeharari"}
last_merge_request_users = {"Cafeine42", "BonaventureEleonore"}
played_musics = []


def convert_time(seconds: int) -> float:
    """Converts seconds to hours and minutes in a 100 base format."""
    worked_hours = 8
    sec_in_hours = 3600
    return round(seconds // sec_in_hours / worked_hours + (seconds % sec_in_hours / worked_hours / 60 / 80), 3) or 0


@bot.command(name="issue", aliases=["t", "issues", "jira", "j"])
async def display_jira_issues(ctx, *issues):
    """
    Displays selected Jira issues

    :param ctx: The context of the command
    :param issues: Issues to display
    :return: The embed containing Jira issues
    """
    if len(issues) == 0:
        embed = discord.Embed(title="", color=0x0052cc)
        embed.add_field(name="", value="No issue provided", inline=False)
        await ctx.send(embed=embed)


@bot.command(name="manager", aliases=["m"])
async def bot_manager(ctx, command=None, sub_command=None, *parameters):
    """
    Manages the bot

    :param ctx: The context of commands
    :param command: The command to execute (gitlab, loop)
    :param sub_command: The sub command to execute
        :gitlab: Manages the Gitlab excluded users list for the Merge Request loop
            :-a: Adds a user to the excluded users list
            :-d: Removes a user from the excluded users list
        :loop: Manages the Merge Request loop
            :-r: Starts the Merge Request loop
            :-s: Stops the Merge Request loop
    :param parameters: The parameters of the sub command
    """

    if command is None:
        await ctx.send("No command provided.")

    elif command in {"-bot", "-b"}:
        if sub_command is None:
            await ctx.send("No bot command provided.")
        elif sub_command in {"-start", "-s"}:
            if "qa" in parameters:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=f"{GITHUB_REPO_URL}/actions/runs",
                                           headers=GITHUB_WORKFLOW_HEADERS) as workflow_runs:
                        workflow_runs = await workflow_runs.json()
                        for workflow_run in workflow_runs["workflow_runs"]:
                            if workflow_run["display_title"] == GITHUB_WORKFLOW_EVENT_QA:
                                last_workflow_run_status = workflow_run["status"]
                                break

                        if last_workflow_run_status == "completed":
                            requests.post(url=f"{GITHUB_REPO_URL}/dispatches",
                                          json={"event_type": GITHUB_WORKFLOW_EVENT_QA},
                                          headers=GITHUB_WORKFLOW_HEADERS)
                            await ctx.send("Démarrage du bot Excel pour la QA")
                        else:
                            await ctx.send("Le bot Excel pour la QA est déjà en cours d'exécution.")
            elif "sales" in parameters:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=f"{GITHUB_REPO_URL}/actions/runs",
                                           headers=GITHUB_WORKFLOW_HEADERS) as workflow_runs:
                        workflow_runs = await workflow_runs.json()
                        for workflow_run in workflow_runs["workflow_runs"]:
                            if workflow_run["display_title"] == GITHUB_WORKFLOW_EVENT_SALES:
                                last_workflow_run_status = workflow_run["status"]
                                break

                        if last_workflow_run_status == "completed":
                            requests.post(url=f"{GITHUB_REPO_URL}/dispatches",
                                          json={"event_type": GITHUB_WORKFLOW_EVENT_SALES},
                                          headers=GITHUB_WORKFLOW_HEADERS)
                            await ctx.send("Démarrage du bot Excel pour le Commerce")
                        else:
                            await ctx.send("Le bot Excel pour le Commerce est déjà en cours d'exécution.")

            else:
                await ctx.send(f"Le bot {parameters} n'existe pas.")
        else:
            await ctx.send("Unknown bot command provided.")

    elif ctx.author.id != DISCORD_ADMIN_ROLE_ID:
        print(ctx.author.id, DISCORD_ADMIN_ROLE_ID)
        await ctx.send("You are not allowed to access the Bot manager panel.")

    elif command in {"-message", "-m"}:
        if sub_command is None:
            await ctx.send("No message command provided.")
        elif sub_command in {"-delete", "-d"}:
            try:
                if parameters:
                    for message_id in parameters:
                        message = await ctx.channel.fetch_message(message_id)
                        print("Deleted:", message.id, message.content or message.embeds[0].title)
                        await message.delete()
                else:
                    async for message in ctx.history(limit=30):
                        if bot.user.id == message.author.id:
                            print("Deleted:", message.id, message.content or message.embeds[0].title)
                            await message.delete()
                            await ctx.message.add_reaction('✅')
                            break
            except discord.errors.NotFound:
                print("Message not found.")
        else:
            await ctx.send("Unknown message command provided.")

    elif command in {"-gitlab", "-g"}:
        if sub_command is None:
            await ctx.send(f"Excluded users:\n ⦁ " + '\n⦁ '.join(gitlab_excluded_users))

        elif not parameters:
            await ctx.send("No parameters provided.")

        elif sub_command in {"-add", "-a"}:
            for gitlab_pseudo in parameters:
                gitlab_excluded_users.add(gitlab_pseudo)
            await ctx.send("Added following users to merge requests checker list: " + ', '.join(parameters))

        elif sub_command in {"-delete", "-d"}:
            for gitlab_pseudo in parameters:
                gitlab_excluded_users.discard(gitlab_pseudo)
            await ctx.send("Removed following users to merge requests checker list: " + ', '.join(parameters))

    elif command in {"-loop", "-l"}:
        if sub_command is None:
            await ctx.send(f"Loop status: {last_merge_request_checker.is_running()}")

        elif sub_command in {"-start", "-on"}:
            print("Starting last_merge_request_checker task loop...")
            last_merge_request_checker.start()
            await ctx.send(f"Loop started")

        elif sub_command in {"-stop", "-off"}:
            print("Stopping last_merge_request_checker task loop...")
            last_merge_request_checker.stop()
            await ctx.send(f"Loop stopped")
    else:
        await ctx.send("Unknown command.")


@bot.command(name="joke", aliases=["blague"])
async def display_random_joke(ctx, kind="global"):
    """
    Displays a random joke

    :param ctx: The context of the command
    :param kind: The kind of joke to display (global, dev, dark, limit, beauf, blondes)
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


@bot.command(name="estimate", aliases=["e"])
async def estimate_time_for_sprints(ctx, *sprints):
    if not sprints:
        await ctx.send("Aucun sprint donné.")
        return
    sprints = sorted(set(sprints))
    params_sprints = tuple(f"Sprint {sprint}_QA" for sprint in sprints)
    sql_query = f"""SELECT DISTINCT SUM(i.`estimate_time`) As 'estimate_time'
    FROM issue AS i
    LEFT JOIN sprint_issues AS si
    ON i.`id` = si.`issue_id`
    RIGHT JOIN sprint AS s 
    ON si.`sprint_id` = s.`id`
    WHERE i.`status` not in ('DONE', 'IN REVIEW', 'TO MODIFY', 'IN PROGRESS', 'TO DEPLOY')
    AND s.`name` in ({', '.join(['%s'] * len(sprints))})
    AND i.`project_id` = (SELECT `id` from project WHERE `key` = '{JIRA_KEY}')"""

    estimate_time = MysqlConnection().fetch_all(sql_query=sql_query, params=params_sprints, output_type="rows")[0][0]
    await ctx.send(
        f"Sprint{'s' if len(sprints) > 1 else ''} QA {', '.join(sprint for sprint in sprints)}\n"
        f"-> Temps estimé : {0 if estimate_time is None else str(convert_time(estimate_time)).replace('.', ',')}")


@bot.command(name="git", aliases=["g", "gitlab"])
async def list_merge_requests(ctx, *arguments):
    """
    List all current merge requests

    :param ctx: The context of the command
    :param arguments: (default: all) The parameters to filter the merge requests (both can be used at the same time)
        :conflicts -> Display only merge requests with conflicts
        :<branch_name> -> Display only merge requests for the given branch
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(GITLAB_API_URL) as resp:
            global previous_last_merge_request_id
            if resp.status != 200:
                print(f"Error {resp.status} while fetching data from Gitlab")
                return

            merge_requests = await resp.json()
            merge_requests = sorted(
                (mr for mr in merge_requests if mr["author"]["username"] not in gitlab_excluded_users),
                key=lambda mr: mr["iid"])

            arguments = list(arguments)
            no_mr_text = f"No merge requests"

            if arguments:
                if "conflicts" in arguments:
                    arguments.remove("conflicts")
                    merge_requests = [mr for mr in merge_requests if mr["has_conflicts"]]
                    no_mr_text += " with conflicts"

                merge_requests = [mr for mr in merge_requests if
                                  (mr["target_branch"] in arguments if arguments else True)]
                if arguments:
                    no_mr_text += f" found on `{'`, `'.join(arguments)}`"

                if not merge_requests:
                    await ctx.send(no_mr_text)
                    return

            sorted_merge_requests = {}
            for mr in merge_requests:
                mr_author = mr["author"]["name"].replace("-", " ").replace("_", " ")
                mr_author = re.sub(r"([a-z])([A-Z])", r"\1 \2", mr_author).replace("  ", " ").title().strip()

                if mr_author not in sorted_merge_requests:
                    sorted_merge_requests[mr_author] = []
                sorted_merge_requests[mr_author].append(mr)

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
    """
    Check for new merge requests

    :return: The embed containing the new merge request
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(GITLAB_API_URL) as resp:
            global previous_last_merge_request_id
            if resp.status != 200:
                print(f"Error {resp.status} while fetching data from Gitlab")
                return
            merge_requests = await resp.json()

            last_merge_request = max(
                (mr for mr in merge_requests if mr["author"]["username"] not in last_merge_request_users),
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

            embed = discord.Embed(title=mr_author,
                                  color=side_color,
                                  description=last_merge_request["title"])
            embed.set_thumbnail(url=last_merge_request["author"]["avatar_url"])

            mr_jira_id = re.search(fr"(?i)^(?:{JIRA_KEY}|{JIRA_OLD_KEY})-(\d+)", last_merge_request['source_branch'])
            if mr_jira_id:
                mr_jira_id = mr_jira_id.groups()[0]
                embed.add_field(name="Lien Jira",
                                value=f"[{JIRA_KEY}-{mr_jira_id}]({JIRA_URL}{JIRA_KEY}-{mr_jira_id})",
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
                    name="⚠️ Merge Conflict ⚠️",
                    value=f"[lien vers conflit]({GITLAB_REPO_URL}/merge_requests/{last_merge_request['iid']}/conflicts)",
                    inline=True)

            channel = bot.get_guild(DISCORD_GUILD_ID).get_channel(DISCORD_CHANNEL_ID)
            await channel.send(embed=embed,
                               content=f"MR {GITLAB_REPO_URL}/merge_requests/{last_merge_request['iid']}")


@bot.listen()
async def on_message(message):
    """
    Check for Jira issues in messages

    :param message: The message to check
    :return: The embed containing the Jira issues
    """
    if message.author.bot:
        return

    if message.author.id == DISCORD_ADMIN_ROLE_ID \
            and re.search(fr"^{command_prefix}m(?:anager)? +-m(?:essage)? +-d(?:elete)?",
                          message.content.strip()
                          ) is not None:
        # await message.add_reaction('✅')
        return

    channel = bot.get_guild(message.guild.id).get_channel(message.channel.id)
    embed = discord.Embed(title="", color=0x0052cc)

    jira_commands = [display_jira_issues.name] + display_jira_issues.aliases
    jira_message_checker = "\\" + command_prefix + \
                           "(?:" + "|".join(jira_commands) + r") +([\d " + JIRA_KEY + JIRA_OLD_KEY + "\-]+)(?<!\s)"
    issue_ids = re.findall(jira_message_checker, message.content.upper(), flags=re.I)
    if not issue_ids:
        return

    issue_ids_fixed = (
        re.sub(fr"({JIRA_KEY}|{JIRA_OLD_KEY})(?: |)(\w+)",
               lambda match_obj: match_obj.group(1) + '-' + match_obj.group(2), x)
        for x in issue_ids)
    issue_ids_split = list(list(dict.fromkeys(
        f"{JIRA_KEY}-{issue_id.strip()}" if issue_id.strip().isdigit() else issue_id for issue_id in
        grouped_ids.split()))
                           for grouped_ids in issue_ids_fixed)
    issue_ids_assembled = reduce(lambda group_1, group_2: group_1 + group_2, issue_ids_split)
    issue_ids_filtered = [issue_id for issue_id in issue_ids_assembled if
                          re.match(rf"({JIRA_KEY}|{JIRA_OLD_KEY})-\d+", issue_id) is not None]

    sql_query = (f"SELECT i.`key`, i.`summary`, gc.`target_branch` "
                 f"FROM `issue` AS i "
                 f"LEFT JOIN gitlab_commit AS gc "
                 f"ON i.key = gc.key "
                 f"WHERE i.`key` IN ({', '.join(['%s'] * len(issue_ids_filtered))})")
    df_issues = MysqlConnection().fetch_all(sql_query=sql_query, params=issue_ids_filtered, output_type="df")

    if not df_issues.shape[0]:
        # TODO: Si issue non trouvé, va directement les requêter sur Jira le issue
        is_plural = 's' if len(issue_ids_filtered) > 1 else ''
        error_message = f"Ticket{is_plural} **{'**, **'.join(issue_ids_filtered)}** inexistant{is_plural} ou supprimé{is_plural}."
        embed.add_field(name="", value=error_message, inline=False)
        await channel.send(embed=embed)
        return

    df_issues = df_issues.set_index("key").reindex(index=issue_ids_filtered).reset_index()
    total_rows = df_issues.shape[0]
    for start_row in range(0, total_rows, 25):
        sub_df_issues = df_issues.iloc[start_row:start_row + 25, :]
        if start_row:
            embed = discord.Embed(title="", color=0x0052cc)
        for issue_data in sub_df_issues.iterrows():
            # TODO: Si ticket non trouvé, va directement les requêter sur Jira le ticket
            issue_data = issue_data[1]
            issue_key = issue_data["key"]
            issue_summary = issue_data["summary"]
            issue_target_branch = issue_data["target_branch"]
            target_branch_text = '' if pd.isna(issue_target_branch) else f"-> [`{issue_target_branch}`]({GITLAB_REPO_URL}/tree/{issue_target_branch})"
            embed.add_field(name="",
                            value=f"[{issue_key}]({JIRA_URL}{issue_key}) {target_branch_text}\n"
                                  f"> **{'Ticket inexistant ou supprimé' if pd.isna(issue_summary) else issue_summary}**",
                            inline=False)

        await channel.send(embed=embed)


# @bot.command(name="play")
# async def play(ctx, music_name: Union[str, None] = None):
#     global voice_client, last_music, last_music_url
#     if music_name is None:
#         await ctx.send("You need to provide a URL.")
#         return
#
#     voice = ctx.author.voice
#
#     if voice is None:
#         await ctx.send("You are not connected to a voice channel.")
#         return
#     channel = voice.channel
#
#     if voice_client is None or not voice_client.is_connected():
#         voice_client = await channel.connect()
#
#     if played_musics and music_name in {music["music_name"] for music in played_musics} and voice_client:
#         if music_name == last_music and voice_client.is_playing():
#             await ctx.send("I am already playing that.")
#         else:
#             await ctx.message.add_reaction("✅")
#             playing_sound = [music for music in played_musics if music["music_name"] == music_name][0]
#             last_music = music_name
#             last_music_url = playing_sound['url']
#             voice_client.stop()
#             voice_client.play(discord.FFmpegPCMAudio(playing_sound['url']))
#     else:
#         await ctx.message.add_reaction("✅")
#         ydl_opts = {
#             'format': 'bestaudio/best',
#             'default_search': 'auto',
#             'source_address': '0.0.0.0'
#         }
#         with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(music_name, download=False)
#
#             if 'entries' in info:
#                 video = info['entries'][0]
#             else:
#                 video = info
#
#             video_url = video['url']
#             last_music = music_name
#             last_music_url = video_url
#             played_musics.append({"music_name": music_name, "url": video_url})
#             if voice_client.is_playing():
#                 voice_client.stop()
#             voice_client.play(discord.FFmpegPCMAudio(video_url))

        # Check if voice channel becomes empty or no sound is playing after 5 minutes
        # minutes_before_disconnecting = 5
        # await asyncio.sleep(minutes_before_disconnecting * 60)
        #
        # if len(channel.members) == 1 or not voice_client.is_playing():
        #     await voice_client.disconnect()
        #     voice_client = None


@bot.command(name="leave")
async def leave(ctx):
    global voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None
        await ctx.message.add_reaction("✅")
    else:
        await ctx.send("I am not connected to a voice channel.")


@bot.command(name="stop")
async def stop(ctx):
    global voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.message.add_reaction("✅")
    else:
        await ctx.send("I am not playing anything.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
