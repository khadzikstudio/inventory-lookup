import numpy as np
from app.database import text_search, get_all_embeddings, get_items_by_ids, get_all_items, get_categories

_embedding_cache = None
_clip_available = False

try:
    from app.clip_engine import encode_text, cosine_similarity
    _clip_available = True
except ImportError:
    pass

SYNONYMS = {
    "furniture": ["sofa", "couch", "chair", "table", "ottoman", "bench", "loveseat",
                  "sectional", "stool", "desk", "cabinet", "shelf", "dresser",
                  "barstool", "lounge", "settee", "recliner", "rocker"],
    "seating": ["chair", "sofa", "couch", "bench", "stool", "ottoman", "loveseat",
                "barstool", "lounge", "settee", "recliner", "rocker", "pouf"],
    "table": ["table", "desk", "console", "cocktail", "bistro"],
    "tables": ["table", "desk", "console", "cocktail", "bistro"],
    "lighting": ["light", "lamp", "chandelier", "sconce", "lantern", "candelabra",
                 "pendant", "led", "neon", "stringer"],
    "lights": ["light", "lamp", "chandelier", "sconce", "lantern", "candelabra",
               "pendant", "led", "neon", "stringer"],
    "linen": ["tablecloth", "napkin", "runner", "overlay", "sash",
              "drape", "curtain", "satin", "velvet", "lamour",
              "bengaline", "organza", "taffeta", "sequin", "polyester"],
    "linens": ["tablecloth", "napkin", "runner", "overlay", "sash",
               "drape", "curtain", "satin", "velvet", "lamour",
               "bengaline", "organza", "taffeta", "sequin", "polyester"],
    "decor": ["vase", "planter", "sculpture", "centerpiece",
              "candle", "mirror", "frame", "wreath", "garland", "floral", "greenery"],
    "bar": ["bar", "bartop", "keg"],
    "outdoor": ["outdoor", "patio", "garden", "tent", "canopy", "umbrella", "yurt",
                "hedge", "planter", "arch"],
    "dinnerware": ["plate", "charger", "glass", "goblet", "flatware",
                   "cup", "bowl", "platter", "china"],
    "sign": ["sign", "led", "neon", "marquee"],
    "signs": ["sign", "led", "neon", "marquee"],
}


def expand_query(query):
    """Expand category terms with synonyms. Returns FTS5-safe OR query."""
    words = query.lower().split()
    terms = set()

    for word in words:
        terms.add(word)
        if word in SYNONYMS:
            for syn in SYNONYMS[word]:
                terms.add(syn)

    return " OR ".join(sorted(terms))


def _load_embeddings():
    global _embedding_cache
    _embedding_cache = get_all_embeddings()
    return _embedding_cache


def invalidate_cache():
    global _embedding_cache
    _embedding_cache = None


def visual_search(query, limit=60):
    if not _clip_available:
        return []

    embeddings = _embedding_cache if _embedding_cache is not None else _load_embeddings()
    if not embeddings:
        return []

    query_vec = encode_text(query)

    scores = []
    for item_id, emb_vec in embeddings:
        sim = cosine_similarity(query_vec, emb_vec)
        scores.append((item_id, sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:limit]


def hybrid_search(query, text_weight=0.4, visual_weight=0.6, limit=60):
    """
    Combine FTS5 text search and CLIP visual search.
    Expands category terms so "blue furniture" finds sofas, chairs, tables, etc.
    """
    if not query or not query.strip():
        return get_all_items(limit=limit)

    expanded = expand_query(query)
    text_results = text_search(expanded, limit=limit * 3)

    vis_results = visual_search(query, limit=limit * 3) if _clip_available else []

    if not vis_results:
        text_weight = 1.0
        visual_weight = 0.0

    text_scores = {}
    if text_results:
        ranks = [abs(r[1]) for r in text_results]
        max_rank = max(ranks) if ranks else 1.0
        if max_rank == 0:
            max_rank = 1.0
        for item_id, rank in text_results:
            text_scores[item_id] = abs(rank) / max_rank

    vis_scores = {}
    if vis_results:
        sims = [r[1] for r in vis_results]
        max_sim = max(sims) if sims else 1.0
        min_sim = min(sims) if sims else 0.0
        sim_range = max_sim - min_sim if max_sim != min_sim else 1.0
        for item_id, sim in vis_results:
            vis_scores[item_id] = (sim - min_sim) / sim_range

    all_ids = set(text_scores.keys()) | set(vis_scores.keys())

    combined = []
    for item_id in all_ids:
        t_score = text_scores.get(item_id, 0.0)
        v_score = vis_scores.get(item_id, 0.0)
        final = text_weight * t_score + visual_weight * v_score
        combined.append((item_id, final))

    combined.sort(key=lambda x: x[1], reverse=True)
    top_ids = [c[0] for c in combined[:limit]]

    items = get_items_by_ids(top_ids)
    return items


def filter_by_category(category, limit=60):
    from app.database import _connect
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM items WHERE category = ? ORDER BY name LIMIT ?",
        (category, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def browse_all(limit=60, offset=0):
    return get_all_items(limit=limit, offset=offset)


def list_categories():
    return get_categories()
