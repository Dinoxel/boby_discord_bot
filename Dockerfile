FROM python:3.8-slim-buster

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

COPY ./src ./src

CMD ["python", "./src/bot.py"]
