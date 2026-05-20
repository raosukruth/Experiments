import os
import time
import tweepy
import json
from typing import Any, Dict, Optional

DEFAULT_DOTENV_FILE = ".env"
DEFAULT_SECRETS_FILE = "credentials.json"


def _load_dotenv_values() -> Dict[str, str]:
    env_path = os.path.join(os.path.dirname(__file__), DEFAULT_DOTENV_FILE)
    if not os.path.exists(env_path):
        return {}

    values: Dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw in env_file:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    return values


def _load_secret_from_dotenv(field: str) -> Optional[str]:
    value = _load_dotenv_values().get(field)
    if value and value.strip():
        return value.strip()
    return None


def _load_secret_from_credentials(field: str) -> Optional[str]:
    credentials_path = os.path.join(os.path.dirname(__file__), DEFAULT_SECRETS_FILE)
    if not os.path.exists(credentials_path):
        return None

    with open(credentials_path, "r", encoding="utf-8") as credentials_file:
        payload = json.load(credentials_file)

    value = payload.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _resolve_twitter_bearer_token() -> str:
    env_token = os.getenv("TWITTER_BEARER_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    dotenv_token = _load_secret_from_dotenv("TWITTER_BEARER_TOKEN")
    if dotenv_token:
        return dotenv_token

    credentials_token = _load_secret_from_credentials("twitter_bearer_token")
    if credentials_token:
        return credentials_token

    with open(os.path.join(os.path.dirname(__file__), "bearer-token.txt"), "r", encoding="utf-8") as token_file:
        return token_file.read().strip()


BEARER_TOKEN = _resolve_twitter_bearer_token()
SEARCH_QUERY = os.getenv(
    "TWITTER_SEARCH_QUERY",
    # Focus on English tweets about building AI, agents, workflows, and tooling — exclude crypto/spam
    "lang:en (\"kaggle\" OR \"hyperparameter tuning\" OR \"AutoML\" OR \"automated machine learning\" OR \"ML pipeline\" OR \"model training\" OR \"image segmentation\" OR \"tabular classification\") (\"stuck\" OR \"help\" OR \"recommendation\" OR \"any good\" OR \"looking for\" OR \"struggling\" OR \"anyone know\") -crypto -is:retweet -is:reply"
)
POLL_INTERVAL = int(os.getenv("TWITTER_POLL_INTERVAL", "60"))  
MAX_RESULTS = int(os.getenv("TWITTER_MAX_RESULTS", "25"))
FETCH_CYCLES = int(os.getenv("TWITTER_FETCH_CYCLES", "1"))
OUTPUT_PATH = os.getenv("OPENCLAW_INGEST_OUTPUT", "ingest_tweets.jsonl")

client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

def fetch_tweets(max_results: int) -> list:
    """Fetch recent tweets matching SEARCH_QUERY."""
    response = client.search_recent_tweets(
        query=SEARCH_QUERY,
        tweet_fields=["id", "text", "author_id", "created_at", "lang"],
        max_results=max_results,
    )
    
    return response.data if response and response.data else []

def write_tweets(tweets: list, output_path: str) -> None:
    """Append tweets to output file as JSON lines."""
    with open(output_path, "a") as f:
        for tweet in tweets:
            f.write(json.dumps({
                "id": tweet.id,
                "text": tweet.text,
                "author_id": tweet.author_id,
                "created_at": str(tweet.created_at),
                "lang": tweet.lang
            }) + "\n")


def run_ingest(
    *,
    fetch_cycles: Optional[int] = None,
    max_results: Optional[int] = None,
    poll_interval: Optional[int] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    actual_fetch_cycles = fetch_cycles if fetch_cycles is not None else FETCH_CYCLES
    actual_max_results = max_results if max_results is not None else MAX_RESULTS
    actual_poll_interval = poll_interval if poll_interval is not None else POLL_INTERVAL
    actual_output_path = output_path if output_path is not None else OUTPUT_PATH

    if actual_fetch_cycles < 1:
        raise ValueError("fetch_cycles must be >= 1")
    if actual_max_results < 1:
        raise ValueError("max_results must be >= 1")

    with open(actual_output_path, "w") as _:
        pass

    target_total = actual_max_results * actual_fetch_cycles
    fetched_total = 0

    for cycle in range(actual_fetch_cycles):
        tweets = fetch_tweets(max_results=actual_max_results)
        if tweets:
            print(
                f"[Ingest] Cycle {cycle + 1}/{actual_fetch_cycles}: fetched {len(tweets)} tweets."
            )
            write_tweets(tweets, output_path=actual_output_path)
            fetched_total += len(tweets)
        else:
            print(f"[Ingest] Cycle {cycle + 1}/{actual_fetch_cycles}: no new tweets found.")

        if cycle < actual_fetch_cycles - 1:
            time.sleep(actual_poll_interval)

    return {
        "status": "ok",
        "fetched": fetched_total,
        "target": target_total,
        "output_path": actual_output_path,
    }

def main() -> None:
    print(f"[Ingest] Starting Twitter ingestion bot. Query: {SEARCH_QUERY}")
    try:
        result = run_ingest()
        print(
            f"[Ingest] Done. Fetched {result['fetched']} tweet(s) out of target {result['target']}."
        )
    except Exception as e:
        print(f"[Ingest] Error: {e}")

if __name__ == "__main__":
    main()
