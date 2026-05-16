# AI Build AI Twitter Reply System

This tool helps you decide when (and how) to reply to Twitter/X posts about building AI, using the AI Build AI project. It keeps things helpful, fact-based, and never spammy.

## What It Does
- Reads a tweet or a batch of tweets (from prompts.txt)
- Checks if a reply about AI Build AI would be genuinely useful
- If so, writes a short, natural reply grounded in approved facts
- Blocks replies in unsafe or irrelevant contexts
- Outputs results as JSON (with a confidence score)


## Setup

1. Create a file called `openai-api.txt` in this folder and put your OpenAI API key inside (no quotes, one line).
2. (Optional) Edit `approved_facts.json` to update the facts used for replies.

## How to Use

**Single tweet:**
```
python3 main.py "Your tweet text here"
```

**Batch mode:**
- Add tweets (one per line) to `prompts.txt`
- Run:
```
python3 main.py --test
```
- Results are saved to `output.json` (overwritten each run)

## Input/Output

**Input:**
- Single tweet (string), or multiple tweets in prompts.txt

**Output (single):**
```
{
  "relevant": true,
  "reason": "Post asks for practical AI workflow resources.",
  "reply": "Hey, you might want to check out AIBuildAI—it's an open-source agent...",
  "safety_flags": [],
  "confidence": 0.87
}
```

**Output (batch):**
```
[
  {
    "question": "...",
    "response": "...",
    "confidence": 0.87
  },
  ...
]
```

## Example

Input (prompts.txt):
```
Building an AI agent for weekly research briefs. Any open-source references?
Anyone here using open-source tools for AI workflow automation?
```

Output (output.json):
```
[
  {
    "question": "Building an AI agent for weekly research briefs. Any open-source references?",
    "response": "Hey, you might want to check out AIBuildAI—it's an open-source agent that handles designing and training AI models automatically. It even supports different tasks like protein prediction and wound segmentation. Could be a neat starting point for your research briefs!",
    "confidence": 0.91
  },
  {
    "question": "Anyone here using open-source tools for AI workflow automation?",
    "response": "Hey, I've been checking out AIBuildAI recently. It’s an agent that handles everything from designing to tuning AI models automatically. Not sure if it fits your needs, but it might be worth a look if you want to automate model building.",
    "confidence": 0.89
  }
]
```


## About `approved_facts.json`

This file contains the official facts and descriptions about the AI Build AI project that the system is allowed to reference in replies. It helps ensure all responses are accurate and grounded.

**Structure:**
```
{
  "project_name": "AIBuildAI",
  "short_description": "AIBuildAI is an open-source agent for designing and training AI models automatically.",
  "approved_facts": [
    "Supports tasks like protein prediction and wound segmentation.",
    "Automates design, coding, training, and tuning of AI models.",
    "Open-source and extensible for different workflows."
  ]
}
```

**How to create or update:**
- Start with a short, accurate project description.
- List only facts you want the system to mention in replies (no hype or unverifiable claims).
- Edit `approved_facts.json` directly, or extract facts from your README or docs.

If you update this file, all future replies will use the new facts.

## Notes
- Replies are only generated if the system is confident and the context is safe.
- All replies are grounded in facts from `approved_facts.json`.
- Results are always in JSON for easy parsing.
