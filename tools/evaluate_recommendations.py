"""Offline recommendation metrics: P@K, R@K, NDCG@K, MRR, coverage and diversity."""

import argparse
import json
import math
from pathlib import Path


def evaluate(rows, k=10):
    precisions, recalls, ndcgs, reciprocal_ranks = [], [], [], []
    recommended, domains, all_items, repeats = set(), [], set(), []
    for row in rows:
        predicted = row.get("predicted", [])[:k]
        relevant = set(row.get("relevant", []))
        all_items.update(row.get("catalog", []))
        hits = [1 if item.get("id") in relevant else 0 for item in predicted]
        precisions.append(sum(hits) / max(1, k))
        recalls.append(sum(hits) / max(1, len(relevant)))
        dcg = sum(hit / math.log2(index + 2) for index, hit in enumerate(hits))
        ideal = sum(1 / math.log2(index + 2) for index in range(min(k, len(relevant))))
        ndcgs.append(dcg / ideal if ideal else 0.0)
        reciprocal_ranks.append(next((1 / (index + 1) for index, hit in enumerate(hits) if hit), 0.0))
        recommended.update(item.get("id") for item in predicted)
        domains.append(len({item.get("domain") for item in predicted if item.get("domain")}) / max(1, len(predicted)))
        prior = set(row.get("prior_impressions", []))
        repeats.append(sum(1 for item in predicted if item.get("id") in prior) / max(1, len(predicted)))
    mean = lambda values: round(sum(values) / max(1, len(values)), 4)
    return {
        f"precision@{k}": mean(precisions), f"recall@{k}": mean(recalls),
        f"ndcg@{k}": mean(ndcgs), "mrr": mean(reciprocal_ranks),
        "coverage": round(len(recommended) / max(1, len(all_items)), 4),
        "diversity": mean(domains), "domain_diversity": mean(domains),
        "repeat_exposure_rate": mean(repeats),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON file containing evaluation rows")
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.input.read_text(encoding="utf-8")), args.k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
