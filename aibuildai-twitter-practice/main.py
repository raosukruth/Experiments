import json
import os
import sys

from tools.client_tool import get_approved_facts, get_client
from tools.pipeline_tool import process_tweet


def main():
    approved_facts = get_approved_facts()
    client = get_client()

    args = sys.argv[1:]

    if args and args[0] == "--test":
        source = "tweets"
        if "--source" in args:
            idx = args.index("--source")
            if idx + 1 < len(args):
                source = args[idx + 1]

        if source == "ingest":
            ingest_path = os.path.join(os.path.dirname(__file__), "ingest_tweets.jsonl")
            with open(ingest_path, "r", encoding="utf-8") as f:
                tweet_objs = [json.loads(line) for line in f if line.strip()]
            prompts = [t["text"] for t in tweet_objs if t.get("text")]
            print(f"[Runner] Reading from ingest_tweets.jsonl ({len(prompts)} tweets)")
        else:
            prompts_path = os.path.join(os.path.dirname(__file__), "tweets.txt")
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts = [line.strip() for line in f if line.strip()]
            print(f"[Runner] Reading from tweets.txt ({len(prompts)} tweets)")

        results = []
        for idx, prompt in enumerate(prompts, 1):
            decision = process_tweet(post_text=prompt, client=client, approved_facts=approved_facts)
            results.append({
                "question": prompt,
                "response": decision.get("reply"),
                "confidence": decision.get("confidence"),
            })
            print(f"Tweet {idx} finished.")
        output_path = os.path.join(os.path.dirname(__file__), "tweet_eval_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(json.dumps(results, indent=2))
        return

    if args:
        post_text = " ".join(args).strip()
    else:
        post_text = input().strip()

    decision = process_tweet(post_text=post_text, client=client, approved_facts=approved_facts)
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
