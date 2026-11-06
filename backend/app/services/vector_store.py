import json
import math
import os
import pickle
import re
from collections import Counter

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

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
        self.model = None
        self._reranker = None
        self._bm25_cache = {}
        self._memory_meta = None
        if not settings.embedding_enabled:
            print("Embedding disabled; using BM25 retrieval only")
        else:
            try:
                from sentence_transformers import SentenceTransformer
                kwargs = {"device": settings.embedding_device} if settings.embedding_device else {}
                self.model = SentenceTransformer(self.model_name, **kwargs)
                self.model.encode(["warm up"], show_progress_bar=False, normalize_embeddings=True)
            except Exception as e:
                print("Model load failed:", e)

        self.index_path = os.path.join(VECTOR_DIR, "faiss.index")
        self.meta_path = os.path.join(VECTOR_DIR, "metadata.json")
        self.legacy_meta_path = os.path.join(VECTOR_DIR, "metadata.pkl")
        self.dimension = 0

    # ---------------- metadata ----------------
    def _load_meta(self):
        if self._memory_meta is not None:
            return self._memory_meta
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["deleted"] = set(meta.get("deleted", []))
                return meta
            except Exception as e:
                print("Meta load failed:", e)
                return None
        if os.path.exists(self.legacy_meta_path):
            try:
                with open(self.legacy_meta_path, "rb") as f:
                    meta = pickle.load(f)
                meta["deleted"] = set(meta.get("deleted", set()))
                return meta
            except Exception as e:
                print("Legacy meta load failed:", e)
        return None

    def _save_meta(self, meta):
        chunks = meta.get("chunks", [])
        dimension = meta.get("dimension", 0)
        deleted = set(meta.get("deleted", set()))
        self._memory_meta = {
            "chunks": chunks,
            "dimension": dimension,
            "deleted": deleted,
        }
        payload = {
            "chunks": chunks,
            "dimension": dimension,
            "deleted": sorted(deleted),
        }
        try:
            os.makedirs(VECTOR_DIR, exist_ok=True)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            print("Meta persist failed; using in-memory index:", e)

    def _meta_mtime(self):
        mtimes = [
            os.path.getmtime(p)
            for p in (self.meta_path, self.legacy_meta_path)
            if os.path.exists(p)
        ]
        return max(mtimes) if mtimes else None

    def _valid_chunks(self, meta, user_id=None):
        deleted = meta.get("deleted", set())
        for pos, chunk in enumerate(meta.get("chunks", [])):
            if pos in deleted:
                continue
            if user_id is not None and chunk.get("user_id") != user_id:
                continue
            yield pos, chunk

    # ---------------- chunking ----------------
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

    def get_chunks_smart(self, texts, chunk_size=500, overlap=50):
        """Structure-aware chunking: keep sentences together where possible."""
        chunks = []
        for text in texts:
            text = (text or "").strip()
            if not text:
                continue
            if len(text) <= chunk_size:
                chunks.append({"content": text, "index": len(chunks)})
                continue
            sentences = re.split(r"(?<=[。！？!?；;\n])", text)
            buf = ""
            for sentence in sentences:
                if not sentence:
                    continue
                if len(sentence) > chunk_size:
                    if buf:
                        chunks.append({"content": buf, "index": len(chunks)})
                        buf = ""
                    for start in range(0, len(sentence), chunk_size - overlap):
                        piece = sentence[start:start + chunk_size]
                        if piece:
                            chunks.append({"content": piece, "index": len(chunks)})
                    continue
                if len(buf) + len(sentence) > chunk_size and buf:
                    chunks.append({"content": buf, "index": len(chunks)})
                    buf = (buf[-overlap:] if overlap > 0 else "") + sentence
                else:
                    buf += sentence
            if buf:
                chunks.append({"content": buf, "index": len(chunks)})
        return chunks

    # ---------------- index ----------------
    def build_index(self, chunks):
        self._save_meta({"chunks": chunks, "dimension": 0, "deleted": set()})
        if os.path.exists(self.index_path):
            try:
                os.remove(self.index_path)
            except OSError as e:
                print("Old vector index remove failed:", e)
        self._bm25_cache = {}
        self.dimension = 0
        if self.model is None:
            return
        try:
            texts = [c["content"] for c in chunks]
            embeddings = self.model.encode(
                texts, show_progress_bar=False, normalize_embeddings=True
            )
            import faiss
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype(np.float32))
            faiss.write_index(index, self.index_path)
            self._save_meta({"chunks": chunks, "dimension": dimension, "deleted": set()})
            if os.path.exists(self.legacy_meta_path):
                try:
                    os.remove(self.legacy_meta_path)
                except OSError:
                    pass
            self.dimension = dimension
            self._bm25_cache = {}
        except Exception as e:
            print("Vector index build failed; BM25 only:", e)

    def mark_deleted(self, chunk_ids):
        meta = self._load_meta()
        if not meta:
            return
        deleted = meta.get("deleted", set())
        for pos, chunk in enumerate(meta.get("chunks", [])):
            if chunk.get("index") in chunk_ids:
                deleted.add(pos)
        meta["deleted"] = deleted
        self._save_meta(meta)
        self._bm25_cache = {}

    # ---------------- BM25 ----------------
    @staticmethod
    def _tokenize(text):
        text = (text or "").lower()
        words = re.findall(r"[a-z0-9_]+", text)
        cjk = re.findall(r"[\u4e00-\u9fff]", text)
        bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
        return words + cjk + bigrams

    def _build_bm25(self, meta, user_id):
        key = (self._meta_mtime(), user_id)
        if key in self._bm25_cache:
            return self._bm25_cache[key]

        docs = []
        for _, chunk in self._valid_chunks(meta, user_id):
            tokens = self._tokenize(chunk.get("content", ""))
            docs.append((chunk, tokens, len(tokens)))
        if not docs:
            return None

        doc_freq = Counter()
        for _, tokens, _ in docs:
            doc_freq.update(set(tokens))
        total_len = sum(length for _, _, length in docs)
        cache = {
            "docs": docs,
            "df": doc_freq,
            "n": len(docs),
            "avgdl": total_len / max(1, len(docs)),
        }
        if len(self._bm25_cache) > 8:
            self._bm25_cache.clear()
        self._bm25_cache[key] = cache
        return cache

    def _bm25_search(self, query, k, meta, user_id):
        cache = self._build_bm25(meta, user_id)
        if not cache:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        k1, b = 1.5, 0.75
        scored = []
        for chunk, tokens, doc_len in cache["docs"]:
            tf = Counter(tokens)
            score = 0.0
            for token in query_tokens:
                frequency = tf.get(token, 0)
                if not frequency:
                    continue
                df = cache["df"].get(token, 0)
                idf = math.log(1 + (cache["n"] - df + 0.5) / (df + 0.5))
                score += idf * (frequency * (k1 + 1)) / (
                    frequency + k1 * (1 - b + b * doc_len / max(1e-9, cache["avgdl"]))
                )
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        max_score = scored[0][0] if scored else 1.0
        results = []
        for score, chunk in scored[:k]:
            item = self._item(chunk, score=score / max_score)
            item["bm25"] = score
            results.append(item)
        return results

    # ---------------- vector ----------------
    def _item(self, chunk, score, distance=None):
        item = {
            "content": chunk.get("content", ""),
            "score": float(score),
        }
        for key in ("doc_id", "filename", "chunk_index"):
            if key in chunk:
                item[key] = chunk[key]
        if distance is not None:
            item["distance"] = float(distance)
        return item

    def _vector_search(self, query, k, meta, user_id):
        if (
            self.model is None
            or not meta.get("dimension")
            or not os.path.exists(self.index_path)
        ):
            return []
        import faiss
        index = faiss.read_index(self.index_path)
        chunks = meta.get("chunks", [])
        deleted = meta.get("deleted", set())
        lookup_k = min(max(k * 5, k + len(deleted)), len(chunks))
        if lookup_k <= 0:
            return []
        query_vec = self.model.encode([query], normalize_embeddings=True)
        distances, indices = index.search(query_vec.astype(np.float32), lookup_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(chunks) or idx in deleted:
                continue
            chunk = chunks[idx]
            if user_id is not None and chunk.get("user_id") != user_id:
                continue
            distance = float(distances[0][i])
            results.append(self._item(chunk, score=1.0 / (1.0 + distance), distance=distance))
            if len(results) >= k:
                break
        return results

    # ---------------- fusion / rerank ----------------
    @staticmethod
    def _fuse(vector_results, bm25_results):
        merged = {}

        def add(items):
            for rank, item in enumerate(items):
                key = (item.get("doc_id"), item.get("chunk_index"), item.get("content", "")[:80])
                entry = merged.setdefault(key, {"item": dict(item), "rrf": 0.0})
                entry["rrf"] += 1.0 / (60 + rank)
                entry["item"]["score"] = max(entry["item"].get("score", 0.0), item.get("score", 0.0))
                if item.get("distance") is not None:
                    entry["item"]["distance"] = item["distance"]
                if item.get("bm25") is not None:
                    entry["item"]["bm25"] = item["bm25"]

        add(vector_results)
        add(bm25_results)
        ordered = sorted(merged.values(), key=lambda x: x["rrf"], reverse=True)
        results = []
        max_score = max((entry["item"].get("score", 0.0) for entry in ordered), default=1.0) or 1.0
        for entry in ordered:
            item = entry["item"]
            item["score"] = round(item.get("score", 0.0) / max_score, 4)
            item["rrf"] = round(entry["rrf"], 6)
            results.append(item)
        return results

    def _rerank(self, query, results, limit):
        try:
            from sentence_transformers import CrossEncoder
            if self._reranker is None:
                self._reranker = CrossEncoder(settings.rerank_model)
            pairs = [[query, item.get("content", "")] for item in results]
            scores = [float(x) for x in self._reranker.predict(pairs)]
            for item, score in zip(results, scores):
                item["rerank_score"] = score
            results.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            low, high = min(scores), max(scores)
            for item in results:
                item["score"] = round((item["rerank_score"] - low) / (high - low + 1e-9), 4)
        except Exception as e:
            print("Rerank failed:", e)
        return results[:limit]

    # ---------------- public API ----------------
    def search(self, query, k=5, user_id=None):
        meta = self._load_meta()
        if not meta:
            return []

        mode = (settings.retrieval_mode or "").strip().lower()
        vector_results = []
        bm25_results = []
        if mode in ("hybrid", "vector"):
            vector_results = self._vector_search(query, k * 3, meta, user_id)
        if mode in ("hybrid", "bm25"):
            bm25_results = self._bm25_search(query, k * 3, meta, user_id)

        if mode == "vector":
            results = vector_results
        elif mode == "bm25":
            results = bm25_results
        else:
            results = self._fuse(vector_results, bm25_results)

        if not results and vector_results:
            results = vector_results
        if not results and bm25_results:
            results = bm25_results
        if settings.rerank_enabled and results:
            results = self._rerank(query, results, k * 2)
        return results[:k]

    def get_all_text(self, user_id=None):
        meta = self._load_meta()
        if not meta:
            return ""
        texts = [chunk.get("content", "") for _, chunk in self._valid_chunks(meta, user_id)]
        return "\n".join(texts)

    def get_chunk(self, doc_id, chunk_index, user_id=None):
        meta = self._load_meta()
        if not meta:
            return None
        for _, chunk in self._valid_chunks(meta, user_id):
            if chunk.get("doc_id") == doc_id and chunk.get("chunk_index") == chunk_index:
                return chunk
        return None

    def clear(self):
        for path in (self.index_path, self.meta_path, self.legacy_meta_path):
            if os.path.exists(path):
                os.remove(path)
        self._memory_meta = None
        self._bm25_cache = {}


vector_store = VectorStore()
