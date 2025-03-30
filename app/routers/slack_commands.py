from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from slack_sdk import WebClient
import os

from app.logging_config import logger
from app.wiki_importer import WikiImporter

router = APIRouter()


@router.post("/slack/commands/reimport")
async def trigger_import(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    logger.info(f"Received Slack command: {payload}")
    channel = payload.get("channel")
    user = payload.get("user")

    logger.info("Triggering WikiImporter via Slack command")
    background_tasks.add_task(WikiImporter().run)

    if channel:
        slack = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        logger.info(f"Sending confirmation to Slack (channel: {channel}, user: {user})")
        slack.chat_postMessage(
            channel=channel,
            text=f"Import Wiki został uruchomiony przez <@{user}>"
        )

    return JSONResponse(content={"status": "ok"})
