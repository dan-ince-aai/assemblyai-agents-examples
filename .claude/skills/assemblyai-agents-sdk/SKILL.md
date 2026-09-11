---
name: assemblyai-agents-sdk
description: Build, deploy and operate AssemblyAI voice agents in Python with the assemblyai-agents SDK, the backend SDK for the Voice Agents API. Use this whenever the user wants a Python voice agent, phone agent, IVR, receptionist, order-line or any call-handling bot; wants to add, host or test tools for one; needs pre-connect (caller lookup) requests, Voice Agents webhooks, phone numbers, outbound calls or human transfers; or mentions assemblyai_agents, VoiceAgent, @tool, agent.serve(), AgentConnection or "agents.assemblyai.com". Trigger even when the user only describes the agent's job in plain language ("make a bot that takes reservations") and never names the SDK.
---

# Building voice agents with `assemblyai-agents`

The platform owns the call: speech to text, text to speech, turn taking,
telephony. You own what the agent knows and can do, and — if you choose — what
it says. The two meet over HTTPS: the platform calls your process for tools,
for a pre-connect lookup, and (with `reply=`) for every reply.

So the deliverable is one Python file: `@tool` functions, optionally a
`decide(turn)` function, a `VoiceAgent(...)` declaration, and `agent.serve()`.
Not a client app, not a web service, not a config of URLs.

`references/sdk-reference.md` is the full API surface. Read it for a signature
or a field name; this file is the shape of the work.

## The whole shape

```python
from assemblyai_agents import VoiceAgent, tool
from assemblyai_agents.replies import Turn, call_tool, say, silence

@tool(timeout_seconds=10)
async def order_status(order_said: str) -> dict:
    """Look up an order by the number the caller read out.

    Args:
        order_said: The order number exactly as the caller said it.
    """
    ...

def decide(turn: Turn):                        # optional
    if turn.pending and turn.pending.name == "order_status":
        return say(f"Order {turn.pending.get('number')} is {turn.pending.get('status')}.")
    if not turn.caller_said:
        return say("Could you read me the order number?")
    return call_tool("order_status", order_said=turn.caller_said)

agent = VoiceAgent(
    name="Northwind order line",
    voice="alba",
    system_prompt="You answer order questions for Northwind. Keep replies short.",
    greeting="Thanks for calling Northwind. Do you have an order number?",
    tools=[order_status],                       # served by this process
    reply=decide,                               # omit → the platform's model talks
)

agent.serve()                                   # PUBLIC_BASE_URL → deploy → serve
```

Two modes, one switch: leave `reply=` out and `system_prompt` shapes the
platform's model; set it and your code decides every turn. There is no third
mode. To use a particular model, call it from inside `decide`.

Every URL the wire needs — each tool, the pre-connect handler, the reply
endpoint — is derived from one address. You never write one into the
declaration.

## Pick a shape

| The user wants | Shape | Copy |
| --- | --- | --- |
| an agent that can look things up and act | tools only (no `reply=`) | `tools_only_agent.py` |
| control over what is said | `reply=decide` | `one_file_agent.py` |
| stages, cost control, a stage that provably cannot do certain things | subagents inside `decide` | `subagents.py` |
| a project: tests, a system of record, a call flow to grow | the starter kit | `starter/` |

Start at the top. Move down only for a stated reason. On a test call a
tools-only agent looked a value up correctly and then answered a different
question — fine for a shop, not for a disclosure. That is when `reply=` earns
its keep.

## Workflow

1. **Install and check credentials.**
   ```bash
   pip install "git+https://github.com/dan-ince-aai/assemblyai-agents-python.git"
   python -c "import assemblyai_agents; print(assemblyai_agents.__version__)"
   ```
   The client reads `ASSEMBLYAI_API_KEY`. If unset, ask where it lives; never
   write a key into source. Default host `https://agents.assemblyai.com`;
   `https://agents.us.assemblyai.com` is the US deployment. Agents live per
   host and ids do not cross — persist the id, never look an agent up by name.

2. **Write the tools.** Bare `@tool` functions with docstrings and type hints
   (rules below). Only use `url=` for a service that already exists elsewhere.

3. **Decide who talks.** No `reply=` → write the system prompt carefully: name
   each tool and say when to call it. With `reply=` → write `decide(turn)`
   returning `say()`, `call_tool()` or `silence()`.

4. **Declare and serve.** `VoiceAgent(...)` at module level, then
   `agent.serve()` under `if __name__ == "__main__"`. The declaration carries
   no address, so tests can import the module.

5. **Get an address.** The platform resolves every URL in DNS at deploy time,
   so `agent.serve()` refuses to run without one — `public_url=` or
   `PUBLIC_BASE_URL`. **The SDK never starts a tunnel.** Development: the
   examples' `expose.py` starts ngrok and yields the URL. Hosting: Railway,
   Render, Fly and Cloud Run give you one (`RENDER_EXTERNAL_URL`,
   `https://$RAILWAY_PUBLIC_DOMAIN`); Modal and Lambda want an ASGI app —
   `serving.asgi(agent, secret=...)`. See the hosting docs and pick one.

6. **Verify, cheapest first.**
   - `agent.hosted_at("https://test.invalid", secret="s").to_request()` — a
     `ConfigurationError` names the exact rule broken, no network. Print
     fields, not a full `model_dump()` (it shows the header secret).
   - Unit-test tools with `assemblyai_agents.testing`.
   - `client.agents.get(agent_id)` — tools and pre-connect point at your host;
     header values come back masked, which is expected.
   - Rehearse whole calls offline, the way `starter/rehearse.py` does. Seconds
     per change; belongs in CI.
   - A real call: `AgentConnection` from a terminal (`[audio]` extra), or a
     phone number. Every tool call and reply prints in your server log.

7. **Attach a phone number** — billable; confirm first.
   `client.phone_numbers.purchase_available(PurchaseAvailablePhoneNumberRequest(...))`,
   or `import_()` + `assign_agent()` for a number you own.

## Writing a tool the SDK accepts

`@tool` derives the schema from the signature and refuses anything the server
would, at import:

- **snake_case name**; not `aai_credit_card_luhn_check` / `aai_pre_connect_context`.
- **Docstring first paragraph** is the description the model reads to decide
  whether to call it. Required. Per-parameter text under `Args:`.
- **Every parameter typed**: `str int float bool list[T] dict[str, T]
  Literal[...] Enum Optional[T] BaseModel`. A default makes it optional.
- **Return annotation** required, JSON-serialisable.
- `timeout_seconds` 1–300 (default 120) — set 5–15 for anything a caller waits
  through. `execution_mode` only `interactive`. `response_instructions` adds
  wording after success/error. `dtmf_collected_arguments` reads a parameter
  from the keypad (phone only; `sensitive` must be stated).
- **Take the caller's words.** The platform refuses a tool call carrying a
  value nobody said. Pass `item_said: str` and read it in the handler
  (`replies.digits_said()`); a value an earlier tool returned is also accepted.
- **Validate in the handler.** A model asked for a value it was never told a
  live call reached `find_policy(policy_number="policy number")`. Return a
  refusal the model can read (`{"found": false, "ask": "…"}`), or raise
  `serving.Refused(422, "…")`.
- **Return what you read**: whatever writes the reply sees the result and
  nothing else.

## Writing `decide`

`Turn` reads the platform's request; the `replies` module handles the wire
contract, which was captured from live sessions:

- **`turn.pending`** is the newest tool result nothing has been said about —
  the cue to speak. The tool message is *not* the last message (the platform
  appends a system note), so do not read `messages[-1]`.
- **`pending.ran` is `False`** when the platform refused or failed the call;
  `pending.note` is its prose. Never report that as the tool's outcome. A
  keypad entry that ended early sets `pending.keypad_incomplete`.
- **`turn.result_of(name)`** reads an earlier result back rather than calling
  again — the caller hears the same silence twice otherwise.
- **`turn.preconnect`** is what a phone call's pre-connect captured
  (`{"reference": "4471", ...}`), delivered as the `aai_pre_connect_context`
  tool result. Counts as established.
- **`call_tool()` drops `None` and `""`** because an empty string counts as
  invented.
- **`silence()`** ends a finished call; an agent cannot hang up.
- **No session id on the request.** State is read out of the transcript. The
  one thing it cannot tell you is what the agent already *said* when the caller
  talked over it — keep a note keyed on a value the call established (the
  starter's `Memo`). Never key on the caller's number; it is not in the body.
- **About ten seconds** to answer, and the caller hears silence. Give any
  model call inside `decide` a timeout well inside that, and a fallback that
  still does the stage's work.

## Subagents, when one prompt is doing too much

Route each turn to a different model, prompt and tool allowlist from inside
`decide` (`subagents.py`). Handing over is your code choosing a different model
for the next turn, not a config change. The allowlist is enforced by *you*:
offer a stage only its tool schemas *and* refuse an out-of-scope call. A
subagent prompt replaces the platform's spoken-output guidance — restate it or
the model emits markdown into speech. Flatten another model's tool history into
plain notes; end the list on a user turn; strip trailing spaces from assistant
lines. Newer Opus models reject `temperature`. Rehearse with real tool schemas
from `declared.spec.parameters`, not `{}`.

## Telephony

- **Pre-connect**: `PreConnectRequest(handler=lookup, returns=[Captured(...)],
  allow_overrides=True)`. Phone only, 800 ms ceiling, fails open. Response
  top-level `greeting` replaces the greeting (needs `allow_overrides=True`);
  `reject: true` aborts. At most two entries. The request body may not carry
  the caller number today — check plausible keys and fail open.
- **Transfers**: `transfer_targets=[HumanTransfer(name, phone_number, mode)]`
  requires `outbound_trunk_id`. Consult fields warm-only.
- **Outbound**: `client.calls.create(CreateCallRequest(from_number, to_number))`;
  `from_number` must be on the account with an agent assigned.
- **Keypad**: a tool with `dtmf_collected_arguments` **refuses WebSocket
  sessions** (1008). Put profiles behind a flag to test from a terminal.
- **Voices**: `alba anna charles estelle eve george giovanni iris jane jean
  juergen lola mary michael paul rafael reid vera`. The API rejects anything
  else with the list.

## Pitfalls the SDK tells you about

| Symptom | Fix |
| --- | --- |
| `ConfigurationError: … needs an address … PUBLIC_BASE_URL` | Set `PUBLIC_BASE_URL` or pass `public_url=`. Nothing hosted can deploy without one. |
| `ValidationError: … URL host … does not resolve` | The address must resolve in public DNS. Real tunnel or real host, not a placeholder. |
| `ConfigurationError: both reply= and llm=` | Two modes only. Drop `llm=`; call the model inside `decide`. |
| `ValidationError: voice: Invalid voice` | Use a name from the list in the message. |
| `… dtmf_collected_arguments[n].sensitive: must be stated` | Set `sensitive=True/False` on every profile. |
| `AuthenticationError` | Wrong key, or the key belongs to the other host. |
| `NotFoundError` from `deploy()` | Handled: it creates again and overwrites the stored id. |
| The agent apologises it cannot access the system | Your process was unreachable or slow. Read your log and the session `timeline` artifact. |
| The model never calls the tool | Sharpen the docstring's first paragraph; name the tool in the prompt. |

## Deliverable checklist

- `agent.py`: `@tool` functions, optional `decide`, a module-level `VoiceAgent`
  with no address in it, `agent.serve()` under `__main__`.
- A hosting choice, written down: which host, where `PUBLIC_BASE_URL` comes from.
- Tests: tools via `assemblyai_agents.testing`; one on
  `agent.hosted_at(...).to_request()`; whole calls offline if `reply=` is set.
- A README snippet: install, env vars, how to run, how to try it.
