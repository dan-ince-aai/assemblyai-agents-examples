# AssemblyAI voice agents: worked examples

Runnable agents built on [`assemblyai-agents`][sdk], the backend SDK for the
AssemblyAI Voice Agents API. Copy one and change it.

The SDK is installed with pip. These are files you clone and edit, which is why
they live here rather than in the SDK repo.

[sdk]: https://github.com/dan-ince-aai/assemblyai-agents-python

## What you are building

The platform owns the call: speech to text, text to speech, turn taking,
telephony. You own what the agent knows and can do, and — if you choose — what
it says. The two meet over HTTPS: the platform calls your process for tools,
for a pre-connect lookup, and (with `reply=`) for every reply.

So an agent is one Python file: `@tool` functions, maybe a `decide(turn)`
function, a `VoiceAgent(...)` declaration, and `agent.serve()`.

```
 caller ──phone / SIP / WebSocket──▶  AssemblyAI  ──HTTPS──▶  your process
                                                              /tools/{name}
                                                              /v1/chat/completions
                                                              /pre-connect/{name}
```

## Pick a shape

Start at the top and move down only for a reason. The first three are one file
each.

| You want | Shape | File |
| --- | --- | --- |
| an agent that can look things up and act | tools only; the platform's model talks | [`tools_only_agent.py`](tools_only_agent.py) |
| control over what is said | `reply=decide`; your code talks | [`one_file_agent.py`](one_file_agent.py) |
| stages, cost control, or a stage that provably cannot do certain things | subagents inside `decide` | [`subagents.py`](subagents.py) |
| a project rather than a script | the starter kit | [`starter/`](starter/) |

## Run one

```bash
git clone https://github.com/dan-ince-aai/assemblyai-agents-examples.git
cd assemblyai-agents-examples

uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
    "git+https://github.com/dan-ince-aai/assemblyai-agents-python.git" httpx

export ASSEMBLYAI_API_KEY=...
brew install ngrok && ngrok config add-authtoken <token>     # development only, see below

.venv/bin/python tools_only_agent.py
```

It gets a public address, deploys the agent (creating it the first time,
updating it after), and serves until you stop it. Point a phone number at the
agent id it prints and call in, or talk to it from a terminal:

```bash
uv pip install --python .venv/bin/python "assemblyai-agents[audio] @ git+https://github.com/dan-ince-aai/assemblyai-agents-python.git"
.venv/bin/python -c "
import asyncio, sys
from assemblyai_agents import AgentConnection
async def main():
    conn = AgentConnection(agent_id=sys.argv[1]); conn.on_agent_transcript(print)
    async with conn: await conn.run()
asyncio.run(main())" agent_...
```

## The one thing every example does the same

```python
with public_address(PORT) as base_url:                      # expose.py, below
    agent.serve(public_url=base_url, secret=SECRET, port=PORT)
```

The platform resolves every URL in DNS when the agent is deployed, so the
address has to exist first. `agent.serve()` binds the declaration to it,
deploys, and serves. Nothing else is wired by hand.

### `expose.py` — the address, in development

**The SDK never starts a tunnel.** It needs an address and does not care where
it came from. On a laptop that means a tunnel, so `expose.py` starts ngrok and
yields the URL; if `PUBLIC_BASE_URL` is already set it starts nothing. It is a
script here, not part of the SDK, because nobody runs a quick tunnel in
production and the SDK should not carry one.

Hosting an agent for real means letting the host give you the address:

| Host | `PUBLIC_BASE_URL` | Entry point |
| --- | --- | --- |
| Railway | `https://$RAILWAY_PUBLIC_DOMAIN` | `python agent.py` — `agent.serve()` reads `PORT` |
| Render | `$RENDER_EXTERNAL_URL` | same |
| Fly, Cloud Run, a VM | the app's URL | same |
| Modal, Lambda | the deployed function's URL | `serving.asgi(agent, secret=...)` |

The [hosting docs](https://www.assemblyai.com/docs/voice-agents/voice-agent-sdk/hosting)
have a file for each.

## What is where

| File | |
| --- | --- |
| `tools_only_agent.py` | A hardware shop: check stock, opening hours, reserve an item. No `reply=`. |
| `one_file_agent.py` | An order line whose every sentence is decided in `decide(turn)`. |
| `subagents.py` | A dental line routed between a cheap authenticating model, a conversational booking model, and a strong recovery model. |
| `starter/` | The same three steps around a project: system of record, staged call flow, offline rehearsal, whole-call tests. |
| `phone.py` | Buy a number and attach an agent (billable; needs `--yes`). |
| `expose.py` | ngrok, for development. |
| `.claude/skills/` | A Claude Code skill that knows the SDK. |

## Working on this repo

Keep each example a single readable file that runs on its own. CI installs the
SDK from its branch and proves every example still binds to an address and
builds a valid declaration, then runs the starter's whole-call tests.

```bash
uv pip install --python .venv/bin/python pytest pytest-asyncio
cd starter && ../.venv/bin/python -m pytest -q && ../.venv/bin/python rehearse.py happy
```
