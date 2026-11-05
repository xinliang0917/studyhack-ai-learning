import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

import pickle
import numpy as np

_VECTOR_DIR_CANDIDATES = []
if os.name == 'nt':
    _VECTOR_DIR_CANDIDATES.append(r'D:\_codex_vector')
_VECTOR_DIR_CANDIDATES.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vector_index")
)
VECTOR_DIR = None
for _d in _VECTOR_DIR_CANDIDATES:
    try:
        os.makedirs(_d, exist_ok=True)
        VECTOR_DIR = _d
        break
    except:
        continue
if VECTOR_DIR is None:
    VECTOR_DIR = _VECTOR_DIR_CANDIDATES[-1]
    os.makedirs(VECTOR_DIR, exist_ok=True)

class VectorStore:
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
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

    def search(self, query, k=5):
        if not os.path.exists(self.index_path):
            return []
        import faiss
        index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            meta = pickle.load(f)
        lookup_k = min(k + len(meta.get("deleted", set())), len(meta["chunks"]))
        query_vec = self.model.encode([query])
        distances, indices = index.search(query_vec.astype(np.float32), lookup_k)
        results = []
        deleted = meta.get("deleted", set())
        for i, idx in enumerate(indices[0]):
            if idx < len(meta["chunks"]) and idx not in deleted:
                results.append({
                    "content": meta["chunks"][idx]["content"],
                    "score": float(distances[0][i]),
                })
                if len(results) >= k:
                    break
        return results

    def get_all_text(self):
        if not os.path.exists(self.meta_path):
            return ""
        with open(self.meta_path, "rb") as f:
            meta = pickle.load(f)
        return "\n".join(c["content"] for c in meta["chunks"] if c.get("index") not in meta.get("deleted", set()))

    def clear(self):
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.meta_path):
            os.remove(self.meta_path)

vector_store = VectorStore()