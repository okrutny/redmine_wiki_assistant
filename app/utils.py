import os
from slack_sdk import WebClient


def send_log_to_slack(message: str):
    slack = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    slack.chat_postMessage(
        channel="#gawel-log",
        text=message
    )
