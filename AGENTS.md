# Building a voice agent with this SDK

Read this before writing code. The full guidance is
`.claude/skills/assemblyai-agents-sdk/SKILL.md` with the API surface in
`.claude/skills/assemblyai-agents-sdk/references/sdk-reference.md`. Claude Code
loads those automatically; every other coding agent should open them now. This
file is the short version.

This repo is the examples. The SDK is a package, installed with pip, at
https://github.com/dan-ince-aai/assemblyai-agents-python.

## What you are building

The platform owns the call: speech to text, text to speech, turn taking,
telephony. You own what the agent knows and can do, and — if you choose — what
it says. The two meet over HTTPS.

The deliverable is one Python file: `@tool` functions, optionally a
`decide(turn)`, a `VoiceAgent(...)`, and `agent.serve()`. Not a client app, not
a web service, not a config of URLs.

## Pick a shape

Copy one, do not assemble from scratch.

| The user wants | Shape | Copy |
| --- | --- | --- |
| an agent that can look things up and act | tools only (no `reply=`) | `tools_only_agent.py` |
| control over what is said | `reply=decide` | `one_file_agent.py` |
| stages, cost control, a stage that provably cannot do certain things | subagents inside `decide` | `subagents.py` |
| a project rather than a script | the full kit | `starter/` |

Every one of them ends the same way:

```python
with public_address(PORT) as base_url:      # expose.py: ngrok, development only
    agent.serve(public_url=base_url, secret=SECRET, port=PORT)
```

`pip install` gives you the package and nothing else. Copy the shape you want
plus `expose.py`, because every shape imports `public_address` from it.
`starter/` ships its own copy.

## Rules that cost a call when broken

- **Two modes.** No `reply=`: `system_prompt` shapes the platform's model, so
  name every tool in it and say when to call it. With `reply=`: your code
  decides every turn. Never both; there is no `llm=`.
- **Tools are hosted here.** A bare `@tool` is served by this process at
  `/tools/{name}` and the deploy points the platform at it. `url=` only for a
  service that already exists elsewhere. There are no client-resident tools.
- **The address comes first.** `agent.serve()` refuses to run without
  `public_url=` or `PUBLIC_BASE_URL`, because the platform resolves every URL
  at deploy time. The SDK never starts a tunnel; `expose.py` does, for
  development. In production the host gives you the address.
- **Never send an argument value the conversation has not established.** The
  platform refuses it and the caller hears silence. Pass the caller's words
  verbatim (`item_said: str`) and read them in the handler. `call_tool()`
  drops empty values.
- **Validate in the handler.** A model asked for a value it was never told a
  live call reached `find_policy(policy_number="policy number")`. Return a
  refusal the model can read.
- **A tool result may be prose.** `pending.ran` is `False` when the platform
  refused or failed the call. Reporting that as the tool's outcome is a lie.
- **No session id on a reply request.** Read state out of the transcript
  (`turn.result_of`, `turn.preconnect`, `turn.answer_following`); keep a note
  only for what the agent already *said* (an interrupted line never comes
  back), keyed on a value the call established.
- **A subagent prompt replaces the platform's** spoken-output guidance.
  Restate it. Flatten another model's tool history into notes.
- **Print and flush** from a serving process.
- **Never write an API key into source.** The client reads
  `ASSEMBLYAI_API_KEY`.

## Checking work without picking up the phone

- `agent.hosted_at("https://test.invalid", secret="s").to_request()` — a
  `ConfigurationError` names the exact rule broken, with no network call.
- `assemblyai_agents.testing` — tools are plain callables; unit-test them.
- `starter/rehearse.py` — the reply logic and the tools in the platform's own
  loop, offline, in milliseconds. Its tests are whole calls.

Then call the number. Every tool call and every reply arrives in your terminal
over HTTPS.

## Working on this repo

Keep each example a single readable file that runs on its own.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
    "git+https://github.com/dan-ince-aai/assemblyai-agents-python.git" httpx pytest pytest-asyncio
cd starter && ../.venv/bin/python -m pytest -q
```

`expose.py` exists twice, at the root and in `starter/`, because a copied
starter has to run on its own. A test pins the two together.
