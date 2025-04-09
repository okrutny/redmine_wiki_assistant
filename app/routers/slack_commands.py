from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import requests

from app.codebase_retriever import CodebaseRetriever
from app.logging_config import logger
from app.wiki_importer import WikiImporter

router = APIRouter()

@router.post("/slack/commands/reimport")
async def trigger_import(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    payload = dict(form)
    logger.info(f"Received Slack command: {payload}")

    user = payload.get("user_id")
    response_url = payload.get("response_url")

    logger.info("Triggering WikiImporter via Slack command")
    background_tasks.add_task(WikiImporter().run)

    if response_url:
        logger.info(f"Sending confirmation via response_url (user: {user})")
        requests.post(response_url, json={
            "text": f"Import Wiki został uruchomiony przez <@{user}>"
        })

    return JSONResponse(content={"status": "ok"})


@router.post("/slack/commands/search_codebase")
async def search_text(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    payload = dict(form)
    logger.info(f"Received Slack command: {payload}")

    query = payload.get('text')

    if not query:
        return {"error": "Missing 'query' parameter"}

    background_tasks.add_task(CodebaseRetriever(query).run)
