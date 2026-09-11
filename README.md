# AssemblyAI voice agents: worked examples

Runnable agents built on [`assemblyai-agents`][sdk], the backend SDK for the
AssemblyAI Voice Agents API. Copy one and change it.

The SDK is installed with pip. These are files you clone and edit, which is why
they live here rather than in the SDK repo.

[sdk]: https://github.com/dan-ince-aai/assemblyai-agents-python

## What you are building

The platform owns the call: speech to text, text to speech, turn taking,
telephony. You own what the agent knows and can do, and optionally what it says.
The two meet over HTTPS, and only over HTTPS, because a phone or SIP call has no
client on the line for the platform to ask.

So an agent is a script that serves your own functions, plus a declaration
pointing the platform at it. Not a client app, and not a web service you write.

```
 caller ──phone / SIP / WebSocket──▶  AssemblyAI  ──HTTPS──▶  your script
                                                              your database
                                                              your model
                                                              your API
```

## Pick a shape

Start at the top and move down only for a reason. The first three are one file
each.

| You want | Shape | File |
| --- | --- | --- |
| an agent that can look things up and act | tools only, the platform's model talks | [`tools_only_agent.py`](tools_only_agent.py) |
| control over what is said | your own replies (`llm=`) | [`one_file_agent.py`](one_file_agent.py) |
| stages, cost control, or a stage that provably cannot do certain things | subagent routing | [`subagents.py`](subagents.py) |
| a project rather than a script | the starter kit | [`starter/`](starter/) |

## Run one

```bash
git clone https://github.com/dan-ince-aai/assemblyai-agents-examples.git
cd assemblyai-agents-examples

uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
    "git+https://github.com/dan-ince-aai/assemblyai-agents-python.git" httpx

export ASSEMBLYAI_API_KEY=...
.venv/bin/python tools_only_agent.py
```

```text
ngrok: https://a1bf-....ngrok-free.app -> http://127.0.0.1:8000
created agent agent_7290244bd8c6439795598a1a04332dc0
serving 'Ridgeway Hardware' on http://0.0.0.0:8000
  [tool] check_stock(item='cordless drill') -> 4 in stock
```

Point a phone number at the agent id it prints, with [`phone.py`](phone.py) or
the dashboard, and a real caller takes the identical path. Stop the script and
the agent is still stored; the tunnel address is what goes away, so redeploy
after restarting.

`ngrok` needs to be on your PATH ([`expose.py`](expose.py) starts it). Set
`PUBLIC_BASE_URL` to a staging host or a deployment and no tunnel is started at
all — that file is a workaround until agent code can be deployed directly, and
it is the only one that knows a tunnel exists.

## The three steps inside every example

```python
with public_address(PORT) as base_url:      # expose.py: starts ngrok
    agent = build(base_url)                 # tool URLs point back at this process
    agent_id = deploy(agent)                # create, or update a stored id
    serve(agent, reply=decide, port=PORT)   # blocks; the platform calls in
```

The order is not stylistic. The API resolves every tool hostname in public DNS
when the agent is created, so the address has to exist first. And the port is
claimed before the deploy, because deploying repoints the stored agent and a
port already held by an earlier run would otherwise leave a live agent whose
tools answer to nothing.

`serve()` answers every route the platform will call, read off the declaration,
on the standard library alone. There is no service to write. If your project
already has a web application, `routes()` returns the same handlers to mount
into it.

## What each one shows

**[`tools_only_agent.py`](tools_only_agent.py)** — a hardware shop. Three tools,
no `llm=`, so the platform's own model runs the conversation and your code only
answers tool calls. This is the right starting point for most agents.

**[`one_file_agent.py`](one_file_agent.py)** — an order line. Adds `llm=`, so the
platform asks *your* endpoint what to say on every turn. The responder is a few
lines of plain Python; swap it for a model, a decision tree, or a retrieval
pipeline and the platform cannot tell the difference, because the seam is the
chat-completions schema.

**[`subagents.py`](subagents.py)** — a dental line, routed between stages. Each
stage has its own model, its own prompt and its own tool allowlist: a cheap
model to check who is on the line, a stronger one for the conversation, the
strongest only when it goes wrong. Reach for it when there are stages, or cost
to control, or a stage that must provably not do certain things.

**[`starter/`](starter/)** — a project rather than a script: a mocked system of
record, five tools, a staged reply engine, an offline rehearsal harness and
whole-call tests. Copy the directory, rename it, and change four files in order.
Its [`AGENTS.md`](starter/AGENTS.md) says which four.

**[`phone.py`](phone.py)** — buy a number and attach it to an agent. Billable, so
nothing happens without `--yes`.

## Building with a coding agent

This repo carries a skill at
[`.claude/skills/assemblyai-agents-sdk`](.claude/skills/assemblyai-agents-sdk).
Claude Code picks it up automatically when you work inside the clone. To have it
everywhere:

```bash
cp -r .claude/skills/assemblyai-agents-sdk ~/.claude/skills/
```

[`AGENTS.md`](AGENTS.md) is the same guidance in the file Codex and other coding
agents read, and there is a second one inside `starter/` so it travels with a
copied project.

## Things that cost a call when you get them wrong

- **Every tool needs `http=`.** A tool without it is answered by a connected
  WebSocket client, so it cannot run on a phone call at all, and the SDK refuses
  to attach a number to an agent that still has one. `Tool.hosted_at(url)` binds
  one to an address the `@tool` decorator could not have known.
- **Never send an argument the caller has not established.** The platform
  refuses a tool call carrying an invented or reworded value, and the refusal
  reaches the caller as silence. A live call once reached
  `find_policy(policy_number="policy number")` — the parameter's own description
  echoed back as its value. Validate in the handler.
- **A tool result may be prose, not JSON.** "The caller did not finish entering
  card_number (too_short), so the tool was not called" is a real result.
  Reporting that as a declined card is a lie to someone about their money.
- **A subagent prompt replaces the platform's**, including the spoken-output
  guidance it normally appends. Without those rules restated, a model reads
  markdown aloud.
- **There is no session id on a reply request.** The body carries the whole
  transcript and nothing naming the call. Read state back out of the transcript;
  for the one thing it cannot tell you, what the agent already said, keep a note
  keyed on a value the call established.
- **A text-driven WebSocket session has no caller turns.** Measured: a
  `conversation.message` with role user never reaches a reply endpoint, and the
  `create_reply` instruction that does is a system message dropped by the next
  turn. Rehearse multi-turn calls offline instead. Real speech is unaffected.
- **Print and flush.** A log that appears only at exit is no use during a call.
- **Never write an API key into source.** The client reads `ASSEMBLYAI_API_KEY`.

## Checking work without picking up the phone

```bash
cd starter
.venv/bin/python rehearse.py happy    # a whole call, offline, in milliseconds
.venv/bin/python -m pytest -q         # whole calls, asserted
```

`rehearse.py` runs the platform's own loop with no network: ask the reply engine
what to say, run any tool it asks for, hand the result back, ask again. It
belongs in CI, and it is how to iterate on a call flow.

## License

MIT.
