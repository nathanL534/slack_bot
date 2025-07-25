import os
from fastapi import APIRouter, Request, HTTPException, Query
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
# from slack_sdk.signature import SignatureVerifier
# from fastapi.responses import JSONResponse

load_dotenv()
client  =WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def send_message(channel, text):
    try:
        client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as e:
        print(f"slack error{e.response['error']}")
    

# router = APIRouter()
# slack = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
# verifier = SignatureVerifier(os.getenv("SLACK_SIGNING_SECRET"))
# bot_user_id = slack.auth_test()["user_id"]



