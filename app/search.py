import numpy as np
from app.database import text_search, get_all_embeddings, get_items_by_ids, get_all_items, get_categories

_embedding_cache = None
_clip_available = False

try:
    from app.clip_engine import encode_text, cosine_similarity
    _clip_available = True
except ImportError:
    pass

# Bidirectional synonym groups — every word in a group expands to all others.
# This means searching ANY word in a group returns items matching ANY other word.
_SYNONYM_GROUPS = [
    # --- Holidays & Seasonal ---
    ["christmas", "holiday", "xmas", "festive", "santa", "ornament", "peppermint",
     "stocking", "nutcracker", "reindeer", "sleigh", "gingerbread", "jingle"],
    ["valentine", "valentines", "heart", "romance", "romantic", "cupid"],
    ["halloween", "spooky", "ghost", "pumpkin", "skeleton", "bat", "witch", "skull"],
    ["easter", "bunny", "egg", "pastel"],
    ["winter", "snow", "snowflake", "snowman", "flocked", "frost", "icicle"],
    ["spring", "blossom", "bloom", "garden", "butterfly"],
    ["tropical", "palm", "tiki", "luau", "hawaiian", "island", "paradise"],
    ["patriotic", "flag", "americana", "july"],

    # --- Furniture ---
    ["furniture", "sofa", "couch", "chair", "table", "ottoman", "bench", "loveseat",
     "sectional", "stool", "desk", "cabinet", "shelf", "dresser", "barstool",
     "lounge", "settee", "recliner", "rocker", "pouf"],
    ["seating", "chair", "sofa", "couch", "bench", "stool", "ottoman", "loveseat",
     "barstool", "lounge", "settee", "recliner", "rocker", "pouf"],
    ["table", "tables", "desk", "console", "cocktail", "bistro", "coffee"],
    ["sofa", "couch", "loveseat", "sectional", "settee"],
    ["chair", "chairs", "stool", "stools", "barstool"],

    # --- Lighting ---
    ["lighting", "light", "lights", "lamp", "chandelier", "sconce", "lantern",
     "candelabra", "pendant", "led", "neon", "stringer", "illuminated", "glow",
     "marquee", "lighted"],
    ["sign", "signs", "led", "neon", "marquee", "lighted"],
    ["candle", "candles", "candelabra", "taper", "votive", "pillar", "tealight"],

    # --- Linens & Fabric ---
    ["linen", "linens", "tablecloth", "napkin", "runner", "overlay", "sash",
     "drape", "drapes", "curtain", "curtains", "fabric", "textile"],
    ["drape", "drapes", "curtain", "curtains", "panel", "backdrop"],
    ["velvet", "satin", "silk", "lamour", "bengaline", "organza", "taffeta",
     "sequin", "polyester", "chiffon", "tulle", "lace"],

    # --- Decor & Florals ---
    ["decor", "decoration", "decorations", "decorative", "centerpiece", "accent"],
    ["floral", "florals", "flower", "flowers", "bloom", "blossom", "bouquet",
     "arrangement", "greenery", "foliage", "fern", "eucalyptus", "ivy"],
    ["wreath", "garland", "greenery", "pine", "fir", "evergreen", "vine"],
    ["vase", "vases", "planter", "planters", "pot", "urn", "vessel", "bowl"],
    ["mirror", "mirrors", "reflective", "mirrored"],

    # --- Structures & Backdrops ---
    ["arch", "arches", "arbor", "pergola", "chuppah", "trellis"],
    ["backdrop", "backdrops", "wall", "panel", "screen", "divider", "partition"],
    ["tent", "canopy", "pavilion", "yurt", "marquee"],
    ["outdoor", "patio", "garden", "tent", "canopy", "umbrella", "yurt",
     "hedge", "planter", "arch", "exterior"],

    # --- Bar & Beverage ---
    ["bar", "bars", "bartop", "keg", "beverage", "cocktail", "drink"],

    # --- Dinnerware & Tabletop ---
    ["dinnerware", "plate", "plates", "charger", "chargers", "glass", "glasses",
     "goblet", "goblets", "flatware", "silverware", "cup", "cups", "bowl",
     "platter", "china", "tableware", "place setting"],

    # --- Colors ---
    ["red", "crimson", "scarlet", "burgundy", "maroon", "ruby", "cardinal", "wine", "cherry"],
    ["blue", "navy", "cobalt", "royal", "sapphire", "teal", "turquoise", "indigo", "azure"],
    ["green", "emerald", "sage", "olive", "forest", "hunter", "lime", "mint", "jade"],
    ["pink", "blush", "rose", "fuchsia", "magenta", "coral", "salmon"],
    ["purple", "violet", "lavender", "plum", "lilac", "amethyst", "mauve"],
    ["orange", "tangerine", "amber", "copper", "rust", "peach", "terracotta"],
    ["gold", "golden", "brass", "gilded", "champagne"],
    ["silver", "chrome", "metallic", "pewter", "platinum", "nickel"],
    ["white", "ivory", "cream", "pearl", "alabaster", "off-white"],
    ["black", "onyx", "ebony", "noir", "matte"],
    ["brown", "walnut", "mahogany", "espresso", "chocolate", "mocha", "tan", "caramel"],
    ["clear", "transparent", "acrylic", "lucite", "glass", "crystal"],

    # --- Materials ---
    ["wood", "wooden", "timber", "oak", "walnut", "mahogany", "birch", "bamboo",
     "reclaimed", "driftwood", "teak", "cedar"],
    ["metal", "iron", "steel", "aluminum", "brass", "copper", "wrought"],
    ["marble", "stone", "granite", "concrete", "slate", "terrazzo"],
    ["rattan", "wicker", "woven", "cane", "bamboo"],

    # --- Styles ---
    ["rustic", "farmhouse", "barn", "country", "burlap", "distressed", "reclaimed"],
    ["modern", "contemporary", "sleek", "minimal", "minimalist", "clean"],
    ["vintage", "retro", "antique", "classic", "old"],
    ["glam", "glamorous", "luxe", "luxury", "opulent", "sparkle", "sequin",
     "crystal", "rhinestone"],
    ["bohemian", "boho", "eclectic", "macrame", "woven"],
    ["industrial", "urban", "loft", "pipe", "exposed", "raw"],
    ["elegant", "formal", "sophisticated", "refined", "classic", "timeless"],

    # --- Event Types ---
    ["wedding", "bridal", "ceremony", "reception", "aisle", "altar", "chapel"],
    ["party", "celebration", "birthday", "fiesta", "gala", "bash"],
    ["corporate", "conference", "meeting", "trade", "expo", "summit"],

    # --- Trees & Plants ---
    ["tree", "trees", "topiary", "palm", "ficus", "fiddle", "olive"],
]

# Build lookup: word -> set of all related words
SYNONYMS = {}
for group in _SYNONYM_GROUPS:
    all_words = set(group)
    for word in group:
        if word not in SYNONYMS:
            SYNONYMS[word] = set()
        SYNONYMS[word].update(all_words)


def expand_query(query):
    """Expand search terms with synonyms and prefix matching.
    Returns an FTS5-safe OR query with broad matching."""
    words = query.lower().split()
    terms = set()

    for word in words:
        terms.add(word)
        terms.add(word + "*")
        if word in SYNONYMS:
            for syn in SYNONYMS[word]:
                terms.add(syn)
                terms.add(syn + "*")
        if word.endswith("s") and word[:-1] in SYNONYMS:
            for syn in SYNONYMS[word[:-1]]:
                terms.add(syn)
                terms.add(syn + "*")
        if (word + "s") in SYNONYMS:
            for syn in SYNONYMS[word + "s"]:
                terms.add(syn)
                terms.add(syn + "*")

    clean = set()
    for t in terms:
        if t.endswith("*"):
            base = t[:-1]
            if base not in terms:
                clean.add(t)
        else:
            clean.add(t)
            clean.add(t + "*")

    return " OR ".join(sorted(clean))


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
    text_results = text_search(expanded, limit=limit * 5)

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
