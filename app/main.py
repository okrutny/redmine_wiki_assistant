from fastapi import FastAPI, Request, BackgroundTasks
import uuid

from app.vectorstore import get_collection
from app.wiki_importer import WikiImporter
from app.routers import search_router
from app.middleware import SlackSignatureMiddleware

app = FastAPI()
app.include_router(search_router.router)
app.add_middleware(SlackSignatureMiddleware)


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

@app.post("/reimport")
def trigger_import(background_tasks: BackgroundTasks):
    importer = WikiImporter()
    background_tasks.add_task(importer.run)
    return {"status": "Import started"}
