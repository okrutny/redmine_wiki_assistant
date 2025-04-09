from fastapi import FastAPI, Request, BackgroundTasks
import uuid

from app.vectorstore import get_collection
from app.routers import slack_events, slack_commands
from app.middleware import SlackSignatureMiddleware

app = FastAPI()
app.include_router(slack_events.router)
app.include_router(slack_commands.router)

app.add_middleware(SlackSignatureMiddleware)
8

@app.get("/")
def hello():
    return {"message": "Hello, world!"}

@app.post("/add")
def add_text(request: Request):
    data = request.json()
    text = data.get("text")
    if not text:
        return {"error": "Missing 'text' field"}

    doc_id = str(uuid.uuid4())
    get_collection().add(documents=[text], ids=[doc_id])
    return {"status": "added", "id": doc_id}
