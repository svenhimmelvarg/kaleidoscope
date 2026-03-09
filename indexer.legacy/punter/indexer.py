import os
from dotenv import load_dotenv
import meilisearch
import sys

load_dotenv()

MEILISEARCH_HOST = os.getenv("VITE_MEILISEARCH_HOST", "127.0.0.1:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "password")
INDEX_NAME = os.getenv("INDEX_NAME", "comfy_outputs_v110")

client = meilisearch.Client(f"http://{MEILISEARCH_HOST}", MEILISEARCH_API_KEY)
index = client.index(INDEX_NAME)


def get(id: str):
    doc = index.get_document(id)
    return vars(doc)


def pretty_print(doc):
    print(f"ID: {doc.get('id', 'N/A')}")
    print(f"Models: {', '.join(doc.get('models', []))}")

    created = doc.get("created")
    if created:
        import datetime

        dt = datetime.datetime.fromtimestamp(created)
        print(f"Created: {dt.strftime('%Y-%m-%d (%A)')}")

    print(f"Source: {doc.get('source', 'N/A')}")

    res = doc.get("resolution", "N/A")
    orientation = doc.get("orientation", "N/A")
    print(f"Resolution: {res} ({orientation})")

    print(f"Workflow: {doc.get('workflow_id', 'N/A')}")
    print(f"Loras: {len(doc.get('loras', []))} entries")
    print()

    texts = doc.get("text", [])
    if texts:
        print("TEXT ENTRIES:")
        for t in texts:
            key = t.get("key", "N/A")
            value = t.get("value", "").strip()
            separator = "─" * 56
            print(f"{separator}")
            print(f"[{key}] {value}")
            print(f"{separator}")


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "get":
        print("Usage: python3 -m punter.indexer get <id>")
        sys.exit(1)

    doc_id = sys.argv[2]
    doc = get(doc_id)
    if doc:
        pretty_print(doc)
    else:
        print(f"Document not found: {doc_id}")


if __name__ == "__main__":
    main()
