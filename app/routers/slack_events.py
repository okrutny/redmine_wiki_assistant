import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.logging_config import logger
from app.routers.search_router import qa

router = APIRouter()

@router.post("/slack/events")
async def handle_slack_events(request: Request):
    logger.debug(f"Received Slack event: {request}")
    payload = await request.json()
    logger.info(f"Received Slack event: {payload}")

    if payload.get("type") == "url_verification":
        return JSONResponse(content={"challenge": payload["challenge"]})

    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "app_mention":
            text = event.get("text")
            channel = event.get("channel")

            question = text.split('>', 1)[-1].strip()
            logger.info(f"Slack mention → question: {question}")

            result = qa({"query": question})
            answer = result["result"]
            sources = result.get("source_documents", [])

            formatted_sources = [
                f"<{os.getenv('REDMINE_WIKI_BASE_URL')}{doc.metadata.get('page').replace(' ', '_')}|{doc.metadata.get('page')} (chunk {doc.metadata.get('chunk_id')})>"
                for doc in sources
            ]
            sources_block = "\n".join(formatted_sources) if formatted_sources else "_sources_missing_"

            slack = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
            try:
                slack.chat_postMessage(
                    channel=channel,
                    text=f"*📥 {question}*\n\n{answer}\n\n📚 *Sources:*\n{sources_block}"
                )
            except SlackApiError as e:
                logger.error(f"Slack error: {e.response['error']}")

    return JSONResponse(content={"ok": True})
