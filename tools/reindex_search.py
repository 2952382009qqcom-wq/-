"""Rebuild optional Meilisearch indexes from the canonical SQL database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from core.cases.models import LegalCase
from core.community.models import CommunityPost
from core.search.client import get_search_client


def main():
    client = get_search_client()
    if client is None:
        raise SystemExit("MEILISEARCH_URL is not configured or the service is unavailable")
    with app.app_context():
        post_index = client.index("community_posts")
        case_index = client.index("legal_cases")
        post_index.update_filterable_attributes(["status", "category", "post_type"])
        case_index.update_filterable_attributes(["status", "verification_status", "legal_domain"])
        post_index.add_documents([{
            "id": row.id, "title": row.title, "body": row.body,
            "category": row.category.slug, "post_type": row.post_type, "status": row.status,
        } for row in CommunityPost.query.all()])
        case_index.add_documents([{
            "id": row.id, "title": row.title, "summary": row.summary,
            "dispute_focus": row.dispute_focus, "judgment_reasoning": row.judgment_reasoning,
            "keywords": row.keywords, "case_number": row.case_number,
            "legal_domain": row.legal_domain, "status": row.status,
            "verification_status": row.verification_status,
        } for row in LegalCase.query.all()])
        print(f"Queued {CommunityPost.query.count()} posts and {LegalCase.query.count()} cases for indexing")


if __name__ == "__main__":
    main()
