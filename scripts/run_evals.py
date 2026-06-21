"""Evaluation runner for myScholar."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def run_evals(base_url: str, dataset_path: str) -> None:
    dataset = Path(dataset_path)
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]

    results = {"passed": 0, "failed": 0, "skipped": 0, "details": []}
    client = httpx.Client(base_url=base_url, timeout=60.0)

    for case in cases:
        cat = case.get("category", "unknown")

        if cat == "image":
            # Test image moderation
            resp = client.post("/api/images", json={
                "session_id": "eval", "prompt": case["prompt"], "style": case.get("style", "geometric")
            })
            data = resp.json()
            expect_refusal = case.get("expect_refusal", False)
            passed = (data.get("moderation", {}).get("allowed", True) != expect_refusal)

        elif cat == "calendar":
            resp = client.get("/api/calendar")
            passed = resp.status_code == 200

        else:
            resp = client.post("/api/chat", json={
                "session_id": "eval", "message": case["message"],
                "madhab": case.get("madhab", "general"), "stream": False
            })
            data = resp.json()
            answer = data.get("answer", "").lower()
            expect_refusal = case.get("expect_refusal", False)
            expect_citation = case.get("expect_citation", False)
            expect_dua = case.get("expect_dua", False)

            passed = True
            reason = []

            if expect_refusal and not any(w in answer for w in ["cannot", "unable", "not permissible", "fabricated", "not authentic", "i cannot", "i'm unable"]):
                passed = False
                reason.append("Expected refusal but got normal response")

            if expect_citation and not data.get("citations"):
                passed = False
                reason.append("Expected citations but got none")

            if expect_dua and not data.get("dua"):
                passed = False
                reason.append("Expected dua but got none")

        status = "✅ PASS" if passed else "❌ FAIL"
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        print(f"[{status}] {case['id']} ({cat})")
        results["details"].append({"id": case["id"], "passed": passed, "category": cat})

    total = results["passed"] + results["failed"]
    pct = round(results["passed"] / total * 100, 1) if total else 0
    print(f"\n{'='*50}")
    print(f"Results: {results['passed']}/{total} passed ({pct}%)")
    print(f"Passed: {results['passed']} | Failed: {results['failed']}")

    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dataset", default="eval/evaluation_dataset.jsonl")
    args = parser.parse_args()
    run_evals(args.base_url, args.dataset)
