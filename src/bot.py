import discord
from discord.ext import commands

from dotenv import load_dotenv, find_dotenv

import os

load_dotenv(find_dotenv())
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='>', intents=intents)


def lb(text):
    """Add line break to the end of the text"""
    return text + "\n"


@bot.command()
async def helper(context):
    return_text = lb("Available commands:")
    available_commands = {"ticket": "ticket [-d, --details] <ticket_id>...",
                          "helper": "helper"}

    for command, detail in available_commands.items():
        return_text += lb(f"`{command}` - {detail}")

    await context.send(return_text)


@bot.command()
async def ticket(context, *tickets):
    return_text = ""

    tickets = tuple(set(tickets))
    for ticket_id in tickets:
        if ticket_id in ("-d", "--details"):
            return_text += lb("details")
            continue

        return_text += lb(f"BOBY-{ticket_id}")

    await context.send(return_text)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
