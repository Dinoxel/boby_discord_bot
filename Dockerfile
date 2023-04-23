FROM gorialis/discord.py

WORKDIR /src

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY /src .

CMD ["python", "./bot.py"]