import json
from pathlib import Path


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


def load_knowledge_base():

    if not KNOWLEDGE_FILE.exists():

        return []

    with open(
        KNOWLEDGE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def retrieve_knowledge(
    query,
    top_k=5
):

    knowledge = load_knowledge_base()

    if not knowledge:
        return []

    # --------------------------------------------------------
    # Try ChromaDB + Sentence Transformers
    # --------------------------------------------------------

    try:

        import chromadb

        from sentence_transformers import (
            SentenceTransformer
        )

        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        collection = client.get_or_create_collection(
            name="iot_fault_knowledge"
        )

        # If collection is empty, populate it.
        if collection.count() == 0:

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

        model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        query_embedding = model.encode(
            [query]
        ).tolist()

        result = collection.query(
            query_embeddings=query_embedding,
            n_results=min(
                top_k,
                collection.count()
            )
        )

        documents = result.get(
            "documents",
            [[]]
        )[0]

        return documents

    except Exception:

        # ----------------------------------------------------
        # Fallback keyword retrieval
        # ----------------------------------------------------

        query_words = set(
            query.lower().split()
        )

        scored = []

        for item in knowledge:

            text = (
                item.get("title", "")
                + " "
                + item.get("sensor", "")
                + " "
                + item.get("parameter", "")
                + " "
                + item.get("condition", "")
                + " "
                + item.get("content", "")
            ).lower()

            score = sum(
                1
                for word in query_words
                if len(word) > 2 and word in text
            )

            scored.append(
                (
                    score,
                    item.get(
                        "content",
                        ""
                    )
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            content
            for score, content in scored[:top_k]
            if score > 0
        ]