import json
from datetime import datetime

from core.models import db
from core.recommendations.models import SearchIndexOutbox

from .client import get_search_client


INDEX_BY_ENTITY = {
    "community_post": "community_posts",
    "legal_case": "legal_cases",
}


def enqueue_index(entity_type, entity_id, payload=None, operation="upsert", commit=False):
    row = SearchIndexOutbox(
        entity_type=str(entity_type),
        entity_id=str(entity_id),
        operation=str(operation),
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.session.add(row)
    if commit:
        db.session.commit()
    return row


def process_outbox(limit=50):
    """Best-effort indexing; database search remains the availability fallback."""
    client = get_search_client()
    if client is None:
        return 0
    rows = SearchIndexOutbox.query.filter_by(processed_at=None).order_by(SearchIndexOutbox.created_at.asc()).limit(limit).all()
    processed = 0
    for row in rows:
        index_name = INDEX_BY_ENTITY.get(row.entity_type)
        if not index_name:
            row.last_error = "unsupported entity type"
            row.retry_count += 1
            continue
        try:
            index = client.index(index_name)
            if row.operation == "delete":
                index.delete_document(str(row.entity_id))
            else:
                payload = json.loads(row.payload_json or "{}")
                payload["id"] = int(row.entity_id) if str(row.entity_id).isdigit() else str(row.entity_id)
                index.add_documents([payload])
            row.processed_at = datetime.utcnow()
            row.last_error = ""
            processed += 1
        except Exception as error:
            row.retry_count += 1
            row.last_error = str(error)[:500]
    db.session.commit()
    return processed
