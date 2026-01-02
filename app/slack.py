import os
from fastapi import APIRouter, Request, HTTPException, Query
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()
client  =WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def send_message(channel, text):
    try:
        client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as e:
        print(f"slack error{e.response['error']}")
