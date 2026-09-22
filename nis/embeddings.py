"""
NIS Dense Embeddings — v0.3-P1
- explicit dependency (sentence-transformers)
- configurable model (CONFIG.embedding_model)
- deterministic for identical input/model
- cached at data/memory/embeddings.json
- invalidation on model/version changes
- graceful fallback to TF-IDF
"""
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import CONFIG

BASE = Path(__file__).parent.parent / "data" / "memory"
CACHE_PATH = BASE / "embeddings.json"

_model = None
_model_name_loaded = None
_load_error = None

def _cache_path() -> Path:
    # Allow CONFIG override
    p = getattr(CONFIG, "embedding_cache_path", "data/memory/embeddings.json")
    path = Path(p)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / p
    return path

def _load_cache() -> Dict:
    path = _cache_path()
    if not path.exists():
        return {"model": CONFIG.embedding_model, "version": CONFIG.embedding_version, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Invalidate if model/version mismatch
        if data.get("model") != CONFIG.embedding_model or data.get("version") != CONFIG.embedding_version:
            return {"model": CONFIG.embedding_model, "version": CONFIG.embedding_version, "entries": {}}
        return data
    except:
        return {"model": CONFIG.embedding_model, "version": CONFIG.embedding_version, "entries": {}}

def _save_cache(data: Dict):
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _hash_key(text: str) -> str:
    # Deterministic key: hash of normalized text + model + version
    norm = text.strip().lower()
    h = hashlib.sha256(f"{CONFIG.embedding_model}:{CONFIG.embedding_version}:{norm}".encode("utf-8")).hexdigest()[:16]
    return h

def _ensure_model():
    global _model, _model_name_loaded, _load_error
    if _model is not None and _model_name_loaded == CONFIG.embedding_model:
        return _model
    if _load_error and _model_name_loaded == CONFIG.embedding_model:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        # Deterministic: no progress bar, trust_remote_code False
        m = SentenceTransformer(CONFIG.embedding_model)
        _model = m
        _model_name_loaded = CONFIG.embedding_model
        _load_error = None
        return _model
    except Exception as e:
        _model = None
        _model_name_loaded = CONFIG.embedding_model
        _load_error = str(e)
        return None

def is_dense_available() -> bool:
    if not CONFIG.USE_DENSE:
        return False
    m = _ensure_model()
    return m is not None

def get_dense_model_error() -> Optional[str]:
    _ensure_model()
    return _load_error

def _cosine_similarity_dense(a, b) -> float:
    # a,b are vectors (list)
    import math
    dot = sum(x*y for x,y in zip(a,b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(y*y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Deterministic embedding for list of texts.
    Returns None if dense not available or fails (caller must fallback).
    Caches per-text.
    """
    if not CONFIG.USE_DENSE:
        return None
    model = _ensure_model()
    if model is None:
        return None
    cache = _load_cache()
    entries = cache.get("entries", {})
    # Determine which need embedding
    to_embed = []
    keys = []
    results = []
    for t in texts:
        key = _hash_key(t)
        keys.append(key)
        if key in entries:
            # Check entry has vector and matches model/version (already invalidated)
            results.append(entries[key]["vector"])
        else:
            to_embed.append(t)
            results.append(None)  # placeholder
    if to_embed:
        try:
            # Encode deterministically: normalize_embeddings False, convert_to_numpy True
            vectors = model.encode(to_embed, normalize_embeddings=False, show_progress_bar=False)
            # vectors is ndarray
            for orig_text, vec in zip(to_embed, vectors):
                key = _hash_key(orig_text)
                vec_list = vec.tolist() if hasattr(vec, "tolist") else list(vec)
                entries[key] = {"vector": vec_list, "text": orig_text[:200], "timestamp": time.time(), "model": CONFIG.embedding_model, "version": CONFIG.embedding_version}
                # Find placeholder and replace
                idx = keys.index(key)
                results[idx] = vec_list
            cache["entries"] = entries
            cache["model"] = CONFIG.embedding_model
            cache["version"] = CONFIG.embedding_version
            cache["updated"] = time.time()
            _save_cache(cache)
        except Exception as e:
            return None
    # Fill any None (should not happen)
    if any(r is None for r in results):
        return None
    return results

def semantic_scores_dense(query: str, docs: List[str]) -> Optional[List[float]]:
    """
    Returns cosine similarity query vs each doc using dense embeddings.
    Deterministic.
    Returns None if dense unavailable -> caller fallback to TF-IDF.
    """
    if not docs:
        return []
    all_texts = [query] + docs
    vecs = embed_texts(all_texts)
    if vecs is None:
        return None
    q_vec = vecs[0]
    d_vecs = vecs[1:]
    scores = [_cosine_similarity_dense(q_vec, d) for d in d_vecs]
    return scores

def intent_scores_dense(query: str, prototypes: Dict[str, List[str]]) -> Optional[Dict[str, float]]:
    """
    Dense intent scoring: for each intent, compute max and mean cosine between query and examples.
    Returns probs dict or None if dense unavailable.
    """
    import math
    # Flatten prototypes
    all_examples = []
    intent_labels = []
    for intent, examples in prototypes.items():
        for ex in examples:
            all_examples.append(ex)
            intent_labels.append(intent)
    # Embed query + examples
    all_texts = [query] + all_examples
    vecs = embed_texts(all_texts)
    if vecs is None:
        return None
    q_vec = vecs[0]
    ex_vecs = vecs[1:]
    # Group by intent
    scores = {}
    idx = 0
    for intent, examples in prototypes.items():
        sims = []
        for _ in examples:
            sim = _cosine_similarity_dense(q_vec, ex_vecs[idx])
            sims.append(float(sim))
            idx += 1
        # Same formula as TF-IDF: 0.6*max + 0.4*mean, then softmax temp 5
        scores[intent] = 0.6*max(sims) + 0.4*(sum(sims)/len(sims)) if sims else 0.0
    # Softmax temp 5
    exps = {k: math.exp(v*5) for k,v in scores.items()}
    total = sum(exps.values()) or 1.0
    probs = {k: v/total for k,v in exps.items()}
    return probs

def clear_cache():
    path = _cache_path()
    if path.exists():
        path.unlink()

def cache_stats() -> Dict:
    cache = _load_cache()
    return {"model": cache.get("model"), "version": cache.get("version"), "entries": len(cache.get("entries", {})), "path": str(_cache_path()), "dense_available": is_dense_available(), "load_error": get_dense_model_error(), "USE_DENSE": CONFIG.USE_DENSE}
