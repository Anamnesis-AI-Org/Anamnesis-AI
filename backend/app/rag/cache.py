"""cache.py — Simple file-based and in-memory cache for API queries and LLM outputs."""

import json
import logging
import hashlib
from pathlib import Path
from functools import wraps

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"
CACHE_FILE = CACHE_DIR / "rag_cache.json"

_in_memory_cache = {}

def init_cache():
    """Ensure cache directory and file exist, and load into memory."""
    global _in_memory_cache
    if not CACHE_DIR.exists():
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("RAG Cache │ Failed to create cache directory: %s", e)
            _in_memory_cache = {}
            return
    
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _in_memory_cache = json.load(f)
            logger.info("RAG Cache │ Loaded %d items from persistent cache", len(_in_memory_cache))
        except Exception as e:
            logger.warning("RAG Cache │ Failed to load cache file: %s. Starting fresh.", e)
            _in_memory_cache = {}
    else:
        _in_memory_cache = {}

def _save_cache():
    """Write in-memory cache to disk (skipped on ephemeral hosts)."""
    from app.config import DISABLE_FILE_CACHE

    if DISABLE_FILE_CACHE:
        return
    try:
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_in_memory_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("RAG Cache │ Failed to save cache to file: %s", e)

def serialize_result(result):
    """Recursively convert objects like Document or dict to standard JSON types."""
    if isinstance(result, list):
        return [serialize_result(x) for x in result]
    if isinstance(result, dict):
        return {k: serialize_result(v) for k, v in result.items()}
    if hasattr(result, "model_dump"):
        return result.model_dump()
    # Check if it is a Document dataclass
    if result.__class__.__name__ == "Document":
        return {
            "__class__": "Document",
            "id": getattr(result, "id"),
            "content": getattr(result, "content"),
            "metadata": getattr(result, "metadata")
        }
    return result

def deserialize_result(result):
    """Recursively convert standard JSON types back to objects if marked."""
    if isinstance(result, list):
        return [deserialize_result(x) for x in result]
    if isinstance(result, dict):
        if result.get("__class__") == "Document":
            from app.rag.document_loader import Document
            return Document(
                id=result["id"],
                content=result["content"],
                metadata=result["metadata"]
            )
        return {k: deserialize_result(v) for k, v in result.items()}
    return result

def get_cached_val(key: str) -> dict | list | str | None:
    """Retrieve value from cache."""
    val = _in_memory_cache.get(key)
    if val is not None:
        return deserialize_result(val)
    return None

def set_cached_val(key: str, value: dict | list | str):
    """Store value in cache and save to disk."""
    _in_memory_cache[key] = serialize_result(value)
    _save_cache()

def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a unique MD5 hash key for function arguments."""
    serializable_args = []
    for arg in args:
        if hasattr(arg, "model_dump"):
            serializable_args.append(arg.model_dump())
        elif hasattr(arg, "__dict__"):
            serializable_args.append(arg.__dict__)
        else:
            serializable_args.append(arg)
            
    serializable_kwargs = {}
    for k, v in kwargs.items():
        if hasattr(v, "model_dump"):
            serializable_kwargs[k] = v.model_dump()
        elif hasattr(v, "__dict__"):
            serializable_kwargs[k] = v.__dict__
        else:
            serializable_kwargs[k] = v

    serialized = json.dumps({"args": serializable_args, "kwargs": serializable_kwargs}, sort_keys=True)
    arg_hash = hashlib.md5(serialized.encode("utf-8")).hexdigest()
    return f"{prefix}:{arg_hash}"

def rag_cache(prefix: str):
    """Decorator to cache functions returning JSON-serializable payloads."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = make_cache_key(prefix, *args, **kwargs)
            cached = get_cached_val(key)
            if cached is not None:
                logger.info("RAG Cache │ Cache HIT for prefix=%s", prefix)
                return cached
            
            logger.info("RAG Cache │ Cache MISS for prefix=%s", prefix)
            result = await func(*args, **kwargs)
            set_cached_val(key, result)
            return result
        return wrapper
    return decorator

# Initialize cache at import time
init_cache()
