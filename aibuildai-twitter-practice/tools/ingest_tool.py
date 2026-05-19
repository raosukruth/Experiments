from __future__ import annotations
from typing import Any, Dict, Optional
from twitter_ingest import run_ingest


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
