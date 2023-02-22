FROM gorialis/discord.py

WORKDIR /bot

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY /src .

ENV DISCORD_TOKEN=[WE WILL GET THIS SOON]
ENV JIRA_ID=[WE WILL GET THIS SOON]
ENV ALPACA_KEY_SECRET=[WE WILL GET THIS SOON]

CMD ["python", "./bot.py"]