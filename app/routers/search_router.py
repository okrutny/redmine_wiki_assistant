import os

from fastapi import APIRouter, Request

from app.utils import get_qa_chain

router = APIRouter()

WIKI_BASE = os.getenv("REDMINE_WIKI_BASE_URL", "")


@router.post("/search")
async def search_text(request: Request):
    data = await request.json()
    query = data.get("query")

    if not query:
        return {"error": "Missing 'query' parameter"}

    result = get_qa_chain()({"query": query})
    answer = result["result"]
    sources = result.get("source_documents", [])

    formatted_sources = [
        {
            "source": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id"),
            "url": f"{WIKI_BASE}{doc.metadata.get('page').replace(' ', '_')}"
        } for doc in sources
    ]

    return {
        "answer": answer,
        "sources": formatted_sources
    }
