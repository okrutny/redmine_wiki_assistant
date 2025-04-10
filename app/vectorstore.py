import os
from functools import lru_cache
from langchain_community.embeddings import OpenAIEmbeddings
import chromadb


class CustomOpenAIEmbeddings(OpenAIEmbeddings):

    def __init__(self, openai_api_key, *args, **kwargs):
        super().__init__(openai_api_key=openai_api_key, *args, **kwargs)

    def _embed_documents(self, texts):
        return super().embed_documents(texts)  # <--- use OpenAIEmbedding's embedding function

    def __call__(self, input):
        return self._embed_documents(input)  # <--- get the embeddings

@lru_cache
def get_collection():
    client = chromadb.PersistentClient(path="chroma_store")

    # noinspection PyTypeChecker
    return client.get_or_create_collection(
        name="wiki",
        embedding_function=CustomOpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    )
