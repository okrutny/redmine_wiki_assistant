import os
import hashlib
import requests
from typing import List
from app.vectorstore import get_collection
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""],
)


class WikiImporter:
    def __init__(self):

        self.api_url = os.getenv("REDMINE_API_URL")
        self.api_key = os.getenv("REDMINE_API_KEY")
        self.project = os.getenv("REDMINE_PROJECT")
        self.headers = {"X-Redmine-API-Key": self.api_key}
        self.collection = get_collection()

    def get_wiki_index(self) -> List[dict]:
        r = requests.get(
            f"{self.api_url}/projects/{self.project}/wiki/index.json",
            headers=self.headers
        )
        r.raise_for_status()
        return r.json().get("wiki_pages", [])

    def get_wiki_page(self, title: str) -> dict:
        r = requests.get(
            f"{self.api_url}/projects/{self.project}/wiki/{title}.json",
            headers=self.headers
        )
        r.raise_for_status()
        return r.json().get("wiki_page", {})

    def hash_chunk(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def split_chunks(self, text: str) -> list[str]:
        return text_splitter.split_text(text)

    def run(self):
        wiki_pages = self.get_wiki_index()
        print(f"Found {len(wiki_pages)} wiki pages")

        for page in wiki_pages:
            title = page["title"]
            updated = page["updated_on"]

            print(f"Importing page: {title}")
            page_data = self.get_wiki_page(title)
            content = page_data.get("text", "")
            chunks = self.split_chunks(content)

            for i, chunk in enumerate(chunks):
                chunk_hash = self.hash_chunk(chunk)
                doc_id = f"{title}_{i}"

                existing = self.collection.get(
                    ids=[doc_id], include=["metadatas"]
                )
                if existing["ids"]:
                    old_hash = existing["metadatas"][0].get("hash")
                    if old_hash == chunk_hash:
                        continue  # no change
                    else:
                        self.collection.delete(ids=[doc_id])

                metadata = {
                    "page": title,
                    "chunk_id": i,
                    "hash": chunk_hash,
                    "updated_at": updated
                }

                self.collection.add(
                    documents=[chunk],
                    ids=[doc_id],
                    metadatas=[metadata]
                )

            print(f"Imported {len(chunks)} chunks for page: {title}")

        print(f"Finished importing")
