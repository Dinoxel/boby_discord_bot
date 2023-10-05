import requests
import os
import json
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

SLACK_HOOK = os.getenv("SLACK_HOOK")
print(SLACK_HOOK)


def send_slack_message():
    last_merge_request = {"labels": ["dev", "WIP"]}

    fields = [
        {
            "type": "mrkdwn",
            "text": "*Branche cible*\n`dev`"
        },
        {
            "type": "mrkdwn",
            "text": "*Lien Jira*\n<https://boby-app.atlassian.com/browse/BB-5469|BB-5469>"
        },
        {
            "type": "mrkdwn",
            "text": f"*Label*\n{' • '.join(label for label in last_merge_request['labels'])}"
        },
        {
            "type": "mrkdwn",
            "text": "*Merge Conflict*\n<https://gitlab.com/cybat/boby-web/-/merge_requests/2889/conflicts|lien vers conflit>"
        }
    ]
    message_text = "MR https://gitlab.com/cybat/boby-web/-/merge_requests/2906"
    image_url = "https://secure.gravatar.com/avatar/ab3046dfccdea6e5ed9d3c74e8fb7c04"
    title = "*Sébastien Juchet*\nBb 4827 desktop mobile creation possibilite de mettre un acompte dont le cumul depasse les 100"

    payload = {
        "text": message_text,
        "attachments": [
            {
                "color": "#2ECC71",  # red: #E74C3C / green: #2ECC71
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "text": title,
                            "type": "mrkdwn"
                        },
                        "accessory": {
                            "type": "image",
                            "image_url": image_url,
                            "alt_text": "Thumbnail Image"
                        },
                        "fields": fields
                    },
                    # {
                    #     "type": "section",
                    #     "text": {
                    #         "type": "mrkdwn",
                    #         "text": "Test block with users select"
                    #     },
                    #     "fields": [
                    #         {
                    #             "type": "mrkdwn",
                    #             "text": "*Merge Conflict*\n<https://gitlab.com/cybat/boby-web/-/merge_requests/2889/conflicts|lien vers conflit>"
                    #         }
                    #     ],
                    #     "accessory": {
                    #         "type": "users_select",
                    #         "placeholder": {
                    #             "type": "plain_text",
                    #             "text": "Select a user",
                    #             "emoji": True
                    #         },
                    #         "action_id": "users_select-action"
                    #     }
                    # }
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url=SLACK_HOOK, data=json.dumps(payload), headers=headers)
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    send_slack_message()
