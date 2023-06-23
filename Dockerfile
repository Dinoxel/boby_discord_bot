FROM gorialis/discord.py

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

COPY ./src ./src

RUN apt-get update && apt-get install -y ffmpeg

CMD ["python", "./src/bot.py"]