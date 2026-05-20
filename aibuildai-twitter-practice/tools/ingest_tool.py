from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from twitter_ingest import run_ingest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TWEETS_FILE = "tweets.txt"
DEFAULT_INGEST_FILE = "ingest_tweets.jsonl"


def ingest_tweets(
    *,
    fetch_cycles: Optional[int] = None,
    max_results: Optional[int] = None,
    poll_interval: Optional[int] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    return run_ingest(
        fetch_cycles=fetch_cycles,
        max_results=max_results,
        poll_interval=poll_interval,
        output_path=output_path,
    )


def load_tweets_from_file(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = file_path or os.path.join(_PROJECT_ROOT, DEFAULT_TWEETS_FILE)
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return [{"id": None, "text": line, "author_id": None, "created_at": None, "lang": "en"} for line in lines]


def load_tweets_from_jsonl(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    import json
    path = file_path or os.path.join(_PROJECT_ROOT, DEFAULT_INGEST_FILE)
    tweets = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tweets.append(json.loads(line))
    return tweets
