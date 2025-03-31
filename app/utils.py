import os
from functools import lru_cache

from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from slack_sdk import WebClient

from app.vectorstore import CustomOpenAIEmbeddings

llm = ChatOpenAI(temperature=0.2, model="gpt-4o-2024-11-20")


@lru_cache
def get_base_retriever():
    chroma = Chroma(
        collection_name="wiki",
        embedding_function=CustomOpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ),
        persist_directory="chroma_store"
    )
    return chroma.as_retriever()


@lru_cache
def get_retriever():
    compressor = LLMChainExtractor.from_llm(llm)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=get_base_retriever()
    )

# @lru_cache
# def get_retriever():
#     return Chroma(
#         collection_name="wiki",
#         embedding_function=CustomOpenAIEmbeddings(
#             openai_api_key=os.getenv("OPENAI_API_KEY")
#         ),
#         persist_directory="chroma_store"
#     ).as_retriever()
#

@lru_cache
def get_qa_chain():
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=get_retriever(),
        return_source_documents=True
    )



def send_log_to_slack(message: str):
    slack = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    slack.chat_postMessage(
        channel="#gawel-log",
        text=message
    )
