# Customer Success Agent

An AI agent that automates the first half of the Customer Success (CS) workflow.

When a new email lands in Gmail, the agent:

1. **Classifies** it — is this a CS-related email? If not, it is ignored.
2. **Flags** CS emails with a Gmail label (`CS`).
3. **Researches** similar past cases by searching both your **Discord** channels and
   your **Gmail** correspondence, and reading how those cases were resolved.
4. **Briefs you on Discord** with a structured message covering:
   1. **What the problem is**
   2. **What the solution is, and who was involved** in resolving similar cases
   3. **A suggested message to send to the client**

> The agent **never** sends a reply to the client. It only prepares the briefing for
> you so you stay in the loop and in control.

---

## Architecture

```
Gmail (poll) ──► Classifier (Claude) ──► is CS? ──no──► ignore
                                          │ yes
                                          ▼
                                   Label thread "CS"  (Gmail)
                                          │
                                          ▼
                        Retriever: search similar cases
                        ┌──────────────┬──────────────┐
                        │ Gmail threads │ Discord msgs │
                        └──────────────┴──────────────┘
                                          │
                                          ▼
                              Analyst (Claude) builds the
                              3-part CS briefing
                                          │
                                          ▼
                          Discord DM / channel message to you
```

The pipeline lives in `cs_agent/pipeline.py`. Each integration is isolated in its own
module so you can swap or mock it.

| Module | Responsibility |
| --- | --- |
| `cs_agent/config.py` | Loads configuration from environment variables |
| `cs_agent/llm.py` | Thin Anthropic SDK wrapper with prompt caching |
| `cs_agent/gmail_client.py` | Poll for new mail, fetch threads, apply the `CS` label |
| `cs_agent/discord_bot.py` | Search Discord channel history + send your briefing |
| `cs_agent/classifier.py` | Decide whether an email is CS-related |
| `cs_agent/retriever.py` | Gather similar past cases from Gmail + Discord |
| `cs_agent/analyst.py` | Generate the structured CS briefing |
| `cs_agent/state.py` | Track which messages were already processed |
| `cs_agent/pipeline.py` | Orchestrate the whole flow |
| `main.py` | Polling entry point |

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

You will need:

- **Anthropic API key** — from <https://console.anthropic.com/>.
- **Gmail OAuth client** — create an OAuth 2.0 *Desktop* client in the
  [Google Cloud Console](https://console.cloud.google.com/apis/credentials), enable the
  **Gmail API**, and download the `credentials.json` into the project root. On first run
  the agent opens a browser to authorize and caches a `token.json`.
- **Discord bot token** — create a bot in the
  [Discord Developer Portal](https://discord.com/developers/applications), enable the
  **Message Content Intent**, invite it to your server with *Read Message History*, and
  copy its token. Get your own user ID (to receive the DM) and the channel IDs you want
  searched by enabling Developer Mode in Discord and right-clicking → *Copy ID*.

### 3. Run

```bash
python main.py            # continuous polling loop
python main.py --once     # process one batch and exit (good for cron)
python main.py --dry-run  # classify + brief, but don't label or send Discord msgs
```

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The tests run the pipeline end-to-end against in-memory fakes for Gmail, Discord, and
Claude, so no live credentials are required.

---

## Notes & next steps

This is an MVP scaffold. Sensible follow-ups:

- Replace the in-memory keyword retrieval with a vector index (embeddings) for better
  "similar case" recall as your history grows.
- Switch Gmail polling to push notifications via Cloud Pub/Sub for real-time response.
- Persist briefings/cases to a datastore (Notion, Postgres) for analytics.
