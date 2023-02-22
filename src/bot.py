import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix='>', intents=discord.Intents.all())


@bot.command()
async def hello_world(context):
    await context.send("Hello Boby!")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
