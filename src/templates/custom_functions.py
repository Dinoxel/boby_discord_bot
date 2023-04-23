import pandas as pd


def get_total_embed_characters(embed):
    fields = [embed.title, embed.description, embed.footer.text, embed.author.name]
    fields.extend([field.name for field in embed.fields])
    fields.extend([field.value for field in embed.fields])
    total = ""
    for item in fields:
        total += str(item) if str(item) != 'Embed.Empty' else ''

    return len(total)


def convert_time(n):
    if pd.isna(n):
        return ''
    hours_in_work_day = 8
    minutes_in_hour = 60
    seconds_in_hour = 3600

    day = n // (hours_in_work_day * seconds_in_hour)
    day_text = [f"{int(day)} jour{'s' if day > 1 else ''}" if day else ""]

    n = n % (hours_in_work_day * seconds_in_hour)
    hour = n // seconds_in_hour
    hour_text = [f"{int(hour)} heure{'s' if hour > 1 else ''}" if hour else ""]

    n %= seconds_in_hour
    minute = n // minutes_in_hour
    minute_text = [f"{int(minute)} minute{'s' if minute > 1 else ''}" if minute else ""]

    return '-> **' + ' '.join(day_text + hour_text + minute_text).strip() + '** estimé'
