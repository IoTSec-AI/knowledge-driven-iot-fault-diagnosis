from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_FILE = (
    PROJECT_ROOT
    / "rag"
    / "knowledge_base.json"
)

CHROMA_DIR = (
    PROJECT_ROOT
    / "rag"
    / "chroma_db"
)


def main():

    if not KNOWLEDGE_FILE.exists():

        print(
            "knowledge_base.json not found."
        )

        return

    with open(
        KNOWLEDGE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        knowledge = json.load(file)

    print(
        f"Loaded {len(knowledge)} knowledge records."
    )

    try:

        import chromadb

        from sentence_transformers import (
            SentenceTransformer
        )

        CHROMA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        # Recreate collection
        try:

            client.delete_collection(
                "iot_fault_knowledge"
            )

        except Exception:

            pass

        collection = client.create_collection(
            name="iot_fault_knowledge"
        )

        model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        documents = [
            item["content"]
            for item in knowledge
        ]

        ids = [
            item["id"]
            for item in knowledge
        ]

        embeddings = model.encode(
            documents
        ).tolist()

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings
        )

        print()
        print(
            "RAG knowledge base built successfully."
        )

        print(
            f"Records indexed: {collection.count()}"
        )

    except Exception as error:

        print()
        print(
            "RAG build failed:"
        )

        print(error)


if __name__ == "__main__":
    main()