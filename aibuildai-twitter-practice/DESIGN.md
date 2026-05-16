
# AI Build AI Twitter Reply System Design (Implementation Overview)

## What This System Does

For each Twitter/X-style post, the system decides if a reply mentioning AI Build AI would be genuinely helpful and safe. It:

- Classifies the post for relevance to AI Build AI (using OpenAI LLM, grounded in approved facts).
- If relevant, generates one short, natural, non-promotional reply (also using the LLM, with varied openings and strict fact grounding).
- Applies safety and tone checks (hard blocks, banned phrases, unverifiable claims).
- Returns a structured result with a confidence score.

## How to Run

- **Single prompt:**
  - `python3 main.py "your tweet text here"`
  - Or: `echo "your tweet text here" | python3 main.py`
- **Batch mode:**
  - Add prompts (one per line) to `prompts.txt`.
  - Run: `python3 main.py --test`
  - Results are written to `output.json` (overwritten each run) and printed to the terminal.

## Input/Output Schema

### Input

Single prompt: string (tweet text)

Batch mode: lines from `prompts.txt`

### Output (single prompt)

```json
{
  "relevant": true,
  "reason": "Post asks for practical AI workflow resources.",
  "reply": "Hey, you might want to check out AIBuildAI—it's an open-source agent...",
  "safety_flags": [],
  "confidence": 0.87
}
```

### Output (batch mode)

```json
[
  {
    "question": "...",
    "response": "...",
    "confidence": 0.87
  },
  ...
]
```

## Decision Flow

1. **Hard block check:** If post triggers a hard block (harassment, self-harm, illegal, etc.), immediately return no reply.
2. **Relevance classification:** LLM classifies post as relevant or not, with a confidence score (>= 0.65 required for relevance).
3. **Reply generation:** If relevant, LLM generates a reply, strictly grounded in approved facts, with a natural, varied opening.
4. **Safety/tone check:** Reply is checked for banned phrases, unverifiable claims, and other tone/safety issues. If flagged, reply is suppressed.
5. **Output:** Returns structured result (see above).

## Safety & Tone Rules

- Hard blocks: harassment, self-harm, illegal activity, etc. (see code for regexes)
- Banned reply patterns: hype, superlatives, sales language, unverifiable claims
- Only facts from `approved_facts.json` may be referenced
- Reply must be natural, not repetitive or templated

## Implementation Details

- Uses OpenAI API (model: gpt-4.1-mini by default)
- Loads API key from `openai-api.txt`
- Loads approved facts from `approved_facts.json`
- CLI supports both single and batch modes
- Batch mode prints progress ("Question N finished.")
- Output is always JSON (single or list)
- Temperature is set high (0.8) for varied replies

## Failure Modes & Mitigations

- False positives: Raise threshold, add non-relevant examples
- False negatives: Expand relevant examples, review low-confidence misses
- Ad-like tone: Enforce banned phrases, rewrite for neutrality
- Hallucinated claims: Restrict to approved facts
- Repetitive replies: Prompt for varied/natural openings
- Unsafe context: Hard-block checks before output

## Input/Output Schema

### Input

```json
{
  "post_text": "string"
}
```

### Output

```json
{
  "relevant": true,
  "reason": "Post asks for practical AI workflow resources.",
  "reply": "If you're looking for practical build examples, AI Build AI might be a useful reference.",
  "safety_flags": [],
  "confidence": 0.87
}
```

Rules:

- `relevant`: boolean.
- `reason`: one-sentence explanation.
- `reply`: string or `null` (must be `null` when not relevant).
- `safety_flags`: list of safety labels.
- `confidence`: float in [0.0, 1.0].

No-reply example:

```json
{
  "relevant": false,
  "reason": "Post is unrelated to AI software building.",
  "reply": null,
  "safety_flags": [],
  "confidence": 0.95
}
```

## Relevance Rules (with examples)

### Relevant

1. Post is about building AI apps, agents, workflows, prompts, or tooling.
2. Post asks for practical implementation help or references.
3. Post compares AI build stacks where AI Build AI is contextually useful.

### Not Relevant

1. Unrelated topics (sports, politics, personal updates).
2. Market commentary without build intent.
3. Sensitive or ambiguous contexts where a mention would feel forced.

### Examples

- "Building an AI agent for weekly research briefs. Any open-source references?" -> relevant.
- "What stack are teams using for production LLM workflows?" -> relevant.
- "Huge win tonight, what a game." -> not relevant.
- "AI stocks are up again." -> not relevant.

## Tone Rules (allowed vs banned phrasing)

### Allowed

- Friendly, specific, concise.
- Helpful suggestion, not a pitch.
- Natural language tied to the post.

Allowed examples:

- "If you're looking for practical build examples, AI Build AI could be useful."
- "This might help: AI Build AI has hands-on workflow examples similar to this."

### Banned

- Hype, superlatives, sales language.
- Generic copy-paste promo text.
- Pressure or urgency CTA wording.

Banned examples:

- "Transform your AI journey with the #1 platform today!"
- "You need this now before you miss out."

## Safety Rules (hard blocks)

If any block triggers, force:

- `relevant = false`
- `reply = null`

Hard blocks:

1. Hate, harassment, abuse.
2. Sexual content involving minors or explicit solicitation.
3. Self-harm/violence/extremism or instructions for harm.
4. Illegal activity guidance.
5. Licensed medical, legal, or financial advice contexts.
6. Doxxing or personal data exposure.
7. Unverifiable claims about AI Build AI.

Example flags: `harassment_context`, `self_harm_context`, `illegal_activity_context`, `unverifiable_claim_risk`.

## Decision Flow (classifier -> generator -> safety check)

1. Classify relevance from `post_text` and output `relevant`, `reason`, `confidence`.
2. If `confidence < 0.65`, treat as not relevant.
3. If relevant, generate exactly one short reply.
4. Run safety and tone checks.
5. If a violation is found, downgrade to no-reply and add flags.
