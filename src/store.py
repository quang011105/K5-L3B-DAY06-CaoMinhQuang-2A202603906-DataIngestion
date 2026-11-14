"""Persistent Chroma cosine search and full snapshot refresh."""
import math
import chromadb
from chromadb.config import Settings


class Store:
    def __init__(self, path, dimensions):
        self.client = chromadb.PersistentClient(str(path), settings=Settings(anonymized_telemetry=False))
        self.dimensions = dimensions

    def collection(self, strategy):
        if strategy not in {"A", "B", "C"}:
            raise ValueError("Unknown strategy")
        return self.client.get_or_create_collection(
            f"economics_{strategy.lower()}", embedding_function=None,
            configuration={"hnsw": {"space": "cosine", "ef_search": 100, "ef_construction": 100, "max_neighbors": 16}})

    def upsert(self, strategy, chunks, vectors):
        if not chunks or len(chunks) != len(vectors) or len({c['chunk_id'] for c in chunks}) != len(chunks):
            raise ValueError("Nonempty unique chunks and matching vectors required")
        if any(len(v) != self.dimensions or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors):
            raise ValueError("Invalid vector")
        collection = self.collection(strategy)
        for offset in range(0, len(chunks), 100):
            batch = chunks[offset:offset+100]
            collection.upsert(ids=[c['chunk_id'] for c in batch], documents=[c['text'] for c in batch],
                              embeddings=vectors[offset:offset+100], metadatas=[c['metadata'] for c in batch])
        # Caller passes the complete owned collection snapshot, including all current sources.
        obsolete = set(collection.get(include=[])['ids']) - {c['chunk_id'] for c in chunks}
        if obsolete:
            collection.delete(ids=sorted(obsolete))
        if collection.count() != len(chunks):
            raise RuntimeError("Stored snapshot count mismatch")

    def search(self, strategy, vector, filters=None):
        if len(vector) != self.dimensions:
            raise ValueError("Query dimension mismatch")
        if filters and (set(filters) != {'chapter'} or type(filters['chapter']) is not int or filters['chapter'] not in {3,4}):
            raise ValueError("Only verified integer chapter filters 3/4 are allowed")
        collection = self.collection(strategy)
        if not collection.count():
            raise RuntimeError("Empty collection; run ingest")
        result = collection.query(query_embeddings=[vector], n_results=min(3, collection.count()),
                                  include=['documents', 'metadatas', 'distances'], **({'where': filters} if filters else {}))
        return [{'chunk_id': identifier, 'text': text, 'metadata': metadata,
                 'distance': distance, 'score': 1-distance}
                for identifier, text, metadata, distance in zip(result['ids'][0], result['documents'][0], result['metadatas'][0], result['distances'][0])]
