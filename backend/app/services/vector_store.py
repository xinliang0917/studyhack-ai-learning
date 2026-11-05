import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

import pickle
import numpy as np

from app.config import settings

_DEFAULT_VECTOR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vector_index"
)
VECTOR_DIR = os.getenv("VECTOR_DIR", _DEFAULT_VECTOR_DIR)
os.makedirs(VECTOR_DIR, exist_ok=True)

class VectorStore:
    def __init__(self):
        self.model_name = settings.embedding_model
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.model.encode(["warm up"], show_progress_bar=False)
        except Exception as e:
            print("Model load failed:", e)
            self.model = None

        self.index_path = os.path.join(VECTOR_DIR, "faiss.index")
        self.meta_path = os.path.join(VECTOR_DIR, "metadata.pkl")
        self.dimension = 384

    def get_chunks(self, texts, chunk_size=500, overlap=50):
        chunks = []
        for text in texts:
            if len(text) <= chunk_size:
                chunks.append({"content": text, "index": len(chunks)})
            else:
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunks.append({"content": text[start:end], "index": len(chunks)})
                    start += chunk_size - overlap
        return chunks

    def build_index(self, chunks):
        texts = [c["content"] for c in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        import faiss
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings.astype(np.float32))
        faiss.write_index(index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump({"chunks": chunks, "dimension": dimension, "deleted": set()}, f)

    def mark_deleted(self, chunk_ids):
        if not os.path.exists(self.meta_path):
            return
        with open(self.meta_path, "rb") as f:
            meta = pickle.load(f)
        if "deleted" not in meta:
            meta["deleted"] = set()
        for i, c in enumerate(meta["chunks"]):
            if c.get("index") in chunk_ids:
                meta["deleted"].add(i)
        with open(self.meta_path, "wb") as f:
            pickle.dump(meta, f)

    def search(self, query, k=5, user_id=None):
        if not os.path.exists(self.index_path) or self.model is None:
            return []
        import faiss
        index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            meta = pickle.load(f)
        deleted = meta.get("deleted", set())
        lookup_k = min(max(k * 5, k + len(deleted)), len(meta["chunks"]))
        if lookup_k <= 0:
            return []
        query_vec = self.model.encode([query])
        distances, indices = index.search(query_vec.astype(np.float32), lookup_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(meta["chunks"]) or idx in deleted:
                continue
            chunk = meta["chunks"][idx]
            if user_id is not None and chunk.get("user_id") != user_id:
                continue
            item = {
                "content": chunk["content"],
                "score": float(distances[0][i]),
            }
            for key in ("doc_id", "filename", "chunk_index"):
                if key in chunk:
                    item[key] = chunk[key]
            results.append(item)
            if len(results) >= k:
                break
        return results

    def get_all_text(self, user_id=None):
        if not os.path.exists(self.meta_path):
            return ""
        with open(self.meta_path, "rb") as f:
            meta = pickle.load(f)
        deleted = meta.get("deleted", set())
        texts = []
        for i, chunk in enumerate(meta["chunks"]):
            if i in deleted:
                continue
            if user_id is not None and chunk.get("user_id") != user_id:
                continue
            texts.append(chunk["content"])
        return "\n".join(texts)

    def clear(self):
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.meta_path):
            os.remove(self.meta_path)

vector_store = VectorStore()