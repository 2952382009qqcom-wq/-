import os


def get_search_client():
    url = os.getenv("MEILISEARCH_URL", "").strip()
    if not url:
        return None
    try:
        import meilisearch

        timeout = max(1, min(int(os.getenv("MEILISEARCH_TIMEOUT_SECONDS", "2")), 15))
        return meilisearch.Client(url, os.getenv("MEILISEARCH_API_KEY", ""), timeout=timeout)
    except Exception:
        return None


def search_ids(index_name, query, *, filters=None, limit=50):
    client = get_search_client()
    if client is None or not str(query or "").strip():
        return None
    options = {"limit": max(1, min(int(limit), 100)), "attributesToRetrieve": ["id"]}
    if filters:
        options["filter"] = filters
    try:
        result = client.index(index_name).search(str(query), options)
        return [str(hit["id"]) for hit in result.get("hits", []) if "id" in hit]
    except Exception:
        return None
