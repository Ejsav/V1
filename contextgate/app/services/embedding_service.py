import hashlib
import re

import numpy as np

from app.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into alphanumeric word tokens."""
    return _TOKEN_RE.findall(text.lower())


def embed_text(text: str) -> list[float]:
    """Deterministic local embedding using the hashing trick.

    The same text always produces the same vector, and texts that share
    words produce vectors pointing in a similar direction. This keeps V1
    free of paid embedding APIs while still supporting cosine similarity.
    """
    dims = settings.embedding_dimensions
    vec = np.zeros(dims, dtype=np.float32)

    for token in _tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[index] += sign

    norm = float(np.linalg.norm(vec))
    if norm > 0.0:
        vec /= norm
    return vec.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors, in the range [-1, 1]."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)
