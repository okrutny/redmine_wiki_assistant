from fastapi import APIRouter, Request
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_community.chat_models import ChatOpenAI

from vectorstore import get_retriever

router = APIRouter()

llm = ChatOpenAI(temperature=0.2, model="gpt-4o-2024-11-20")

retriever = get_retriever()

qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)


@router.post("/search")
async def search_text(request: Request):
    data = await request.json()
    query = data.get("query")

    if not query:
        return {"error": "Missing 'query' parameter"}

    result = qa({"query": query})
    answer = result["result"]
    sources = result.get("source_documents", [])

    formatted_sources = [
        {
            "source": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id")
        } for doc in sources
    ]

    return {
        "answer": answer,
        "sources": formatted_sources
    }
