import os
import hashlib
import requests
from typing import List

from app.utils import send_log_to_slack
from app.vectorstore import get_collection
from langchain.text_splitter import RecursiveCharacterTextSplitter


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

    @staticmethod
    def build_page_lookup(wiki_pages):
        return {page["title"]: page for page in wiki_pages}

    @staticmethod
    def build_breadcrumbs(title: str, page_lookup: dict) -> str:
        breadcrumbs = []
        while title:
            page = page_lookup.get(title)
            if not page:
                break
            breadcrumbs.insert(0, title)
            parent = page.get("parent", {}).get("title")
            title = parent
        return " / ".join(breadcrumbs)

    def get_wiki_index(self) -> List[dict]:
        r = requests.get(
            f"{self.api_url}/projects/{self.project}/wiki/index.json",
            headers=self.headers
        )
        r.raise_for_status()
        return r.json().get("wiki_pages", [])

    def get_wiki_page(self, title: str) -> dict:
        r = requests.get(
            f"{self.api_url}/projects/{self.project}/wiki/{title}.json?include=attachments",
            headers=self.headers
        )
        r.raise_for_status()
        return r.json().get("wiki_page", {})

    @staticmethod
    def download_text_attachments(wiki_page: dict, headers: dict):
        attachments = wiki_page.get("attachments", [])
        if not attachments:
            print("Brak załączników do pobrania.")
            return

        text_attachments = {}

        for attachment in attachments:
            filename = attachment.get("filename")
            content_url = attachment.get("content_url")
            if not filename or not content_url:
                continue

            # Sprawdzamy, czy rozszerzenie wskazuje na plik tekstowy
            if filename.lower().endswith((".txt", ".md", ".csv", ".json", ".xml", ".html", ".log")):
                print(f"Pobieram tekstowy załącznik {filename} z {content_url}")
                response = requests.get(content_url, headers=headers)
                response.raise_for_status()
                text_attachments[filename] = response.text
            else:
                print(f"Pomiń załącznik {filename} - nie jest tekstowy.")

        return text_attachments

    def hash_chunk(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def split_chunks(text: str) -> list[str]:
        return text_splitter.split_text(text)

    def fetch_existing_ids(self):
        existing_chunks = self.collection.get()
        existing_ids = set(existing_chunks.get("ids", []))
        return existing_ids

    @staticmethod
    def get_chunk_with_path(chunk: str, path: str) -> str:
        return f"[{path}]\n{chunk}"

    def add_to_collection(self, title: str, index: int, chunk_hash: str, updated: str, path: str,
                          chunk_with_path: str, doc_id: str):
        metadata = {
            "page": title,
            "chunk_id": index,
            "hash": chunk_hash,
            "updated_at": updated,
            "path": path
        }

        self.collection.add(
            documents=[chunk_with_path],
            ids=[doc_id],
            metadatas=[metadata]
        )

    def run(self):
        send_log_to_slack("📥 Wiki import has started.")
        wiki_pages = self.get_wiki_index()
        print(f"Found {len(wiki_pages)} wiki pages")
        page_lookup = self.build_page_lookup(wiki_pages)

        existing_ids = self.fetch_existing_ids()

        imported_ids = set()

        for page in wiki_pages:
            title = page["title"]
            path = self.build_breadcrumbs(title, page_lookup)
            updated = page["updated_on"]

            print(f"Importing page: {title}")
            page_data = self.get_wiki_page(title)
            content = page_data.get("text", "")

            chunks = self.split_chunks(content)

            for i, chunk in enumerate(chunks):
                chunk_with_path = self.get_chunk_with_path(chunk, path)
                chunk_hash = self.hash_chunk(chunk_with_path)
                doc_id = f"{title}_{i}"
                imported_ids.add(doc_id)

                existing = self.collection.get(ids=[doc_id], include=["metadatas"])
                if existing["ids"]:
                    old_hash = existing["metadatas"][0].get("hash")
                    if old_hash == chunk_hash:
                        pass
                    else:
                        print(f"📝 Updated chunk: {doc_id}")
                        send_log_to_slack(f"📝 Updated chunk: {doc_id}")
                        self.collection.delete(ids=[doc_id])
                        self.add_to_collection(title, i, chunk_hash, updated, path, chunk_with_path, doc_id)
                else:
                    print(f"➕ New chunk: {doc_id}")
                    send_log_to_slack(f"➕ New chunk: {doc_id}")
                    self.add_to_collection(title, i, chunk_hash, updated, path, chunk_with_path, doc_id)

                # Pobieramy załączniki tekstowe
                text_attachments = self.download_text_attachments(page_data, self.headers)
                for filename, text_content in text_attachments.items():
                    attachment_chunks = self.split_chunks(text_content)
                    for j, att_chunk in enumerate(attachment_chunks):
                        doc_id = f"{title}_attachment_{filename}_{j}"
                        existing_attachment_ids = self.collection.get(ids=[doc_id], include=["metadatas"])
                        if existing_attachment_ids["ids"]:
                            continue
                        imported_ids.add(doc_id)
                        metadata = {
                            "page": title,
                            "attachment": filename,
                            "chunk_id": j,
                            "updated_at": updated,
                            "path": path
                        }
                        print(f"➕ Dodaję fragment załącznika: {doc_id}")
                        send_log_to_slack(f"➕ Dodaję fragment załącznika: {doc_id}")
                        self.collection.add(
                            documents=[att_chunk],
                            ids=[doc_id],
                            metadatas=[metadata]
                        )

            print(f"✅ Imported {len(chunks)} chunks for page: {title}")

        # Find and delete removed chunks
        deleted_ids = existing_ids - imported_ids
        if deleted_ids:
            for doc_id in deleted_ids:
                print(f"❌ Deleted chunk: {doc_id}")
                send_log_to_slack(f"❌ Deleted chunk: {doc_id}")
            self.collection.delete(ids=list(deleted_ids))

        print(f"🎉 Finished importing")
        send_log_to_slack("✅ Wiki import has completed.")


