---
name: voice-agent-phone-features
description: Add phone-line features to an AssemblyAI voice agent built with the assemblyai-agents SDK - transfer to a person (cold or warm with a briefing), outbound calls, voicemail on outbound calls, keypad (DTMF) entry including card numbers, a caller-ID lookup before the call is answered (pre-connect), caller ID, phone numbers and call webhooks. Use this when the user wants the agent to hand off to a human, call people, take keypad input, recognise the caller, or work on a real phone number.
---

# Phone features

Everything here is a field on `VoiceAgent` or a call on `Client`. Signatures
are in `assemblyai-agents-sdk/references/sdk-reference.md`; this is when and
how to use each one. All of them are inert on a WebSocket session, so test
them on a real call.

## Transfer to a person

```python
from assemblyai_agents import HumanTransfer

transfer_targets=[
    HumanTransfer(name="front desk", phone_number="+14155550100"),            # cold
    HumanTransfer(name="billing", phone_number="+14155550101", mode="warm",
                  consult_instructions="Give the caller's name and what they need in one sentence.",
                  consult_timeout=45),
]
```

- Numbers are E.164. Consult fields are warm-only and refused on a cold one.
- Declaring a target is what gives the model the `aai_transfer_call` tool, so
  name each target in the prompt and say when to use it ("transfer to billing
  for anything about an invoice").
- The platform dials transfers out on its own trunk and ignores
  `outbound_trunk_id`. The SDK's main branch no longer asks for it; the branch
  these examples pin still refuses a transfer without one, so follow
  `assemblyai-agents-sdk` for the version you have installed.
- With `reply=`, the transfer is a tool call your `decide` returns like any
  other; check the caller agreed before returning it.

**Warm or cold.** Warm when the person picking up needs context (billing,
escalations, hot leads); cold when any person will do (front desk). A warm
transfer adds the consult call's length to the caller's wait.

## Outbound calls

```python
from assemblyai_agents.models.rest import CreateCallRequest

call = client.calls.create(CreateCallRequest(from_number="+14155550123", to_number="+12125550148"))
```

- `from_number` must be on the account with an agent assigned; that agent runs
  the call. Placing a call is billable and reaches a real person: confirm the
  numbers with the user before running anything that dials.
- The agent speaks first, so the greeting says who is calling and why, in one
  sentence.
- To tell the agent which booking or account a call is about, look it up in a
  pre-connect request keyed on `dialed_number` rather than encoding it in the
  prompt.
- Respect calling windows and consent rules for the region; put the window in
  the job that places calls, not in the agent.

**Voicemail.** Nothing tells the agent a machine answered, so detect it from
the words: a first caller turn like "leave a message after the tone" or "is
not available". In `decide`, check `turn.caller_said` for those phrases on the
first turn, then `say()` a short message (who, why, how to call back) and
return `silence()`. Without `reply=`, put the same rule in the system prompt.
An agent cannot hang up; silence ends the call.

## Keypad entry (DTMF)

Use the keypad for anything a caller should not say aloud or that speech gets
wrong: card numbers, PINs, long account numbers.

```python
from assemblyai_agents.models.rest import DtmfCollectionProfile

@tool(timeout_seconds=120, dtmf_collected_arguments=[
    DtmfCollectionProfile(parameter_name="card_number", min_digits=15, max_digits=16,
                          sensitive=True, confirm=True,
                          prompt="Using your keypad, enter your card number, then press pound."),
])
async def take_payment(card_number: str, amount: float) -> dict:
    """Charge the caller's card for the order total."""
```

- `sensitive` must be stated on every profile. `True` keeps the value out of
  speech, transcripts and recordings.
- A keypad tool **refuses WebSocket sessions**. Put the profiles behind a flag
  so the agent can still be tested from a terminal.
- Your endpoint never sees keypad parameters in the schema, and an early
  hang-up returns prose, not your tool's JSON. Read `pending.ran` and
  `pending.keypad_incomplete`.
- Validate a card number with a Luhn check in your own tool before charging.
- Prefer a payment link to card entry when the business allows it.

## Know the caller before answering (pre-connect)

Up to two HTTPS requests run before the call is answered, typically a CRM
lookup by the caller's number. Use it to greet a returning caller by name,
skip verification for a known number, or route VIPs.

```python
from assemblyai_agents import Captured, PreConnectRequest

pre_connect=[PreConnectRequest(
    handler=lookup_caller,                              # served by this process
    sends=["caller_number"],
    returns=[Captured(name="first_name", path="customer.first_name", default=""),
             Captured(name="tier", path="customer.tier", default="standard")],
    timeout_ms=400,
    allow_overrides=True,                               # a top-level "greeting" replaces it
)]
```

- 800 ms ceiling. It fails open, so a slow CRM means a normal call, not a
  dead one. Keep the handler to one indexed query.
- The caller number can be withheld; the payload then omits it. Handle that.
- Captures reach the model as the `aai_pre_connect_context` tool result and
  `decide` as `turn.preconnect`. Say in the prompt how to use them.
- Header values are stored on the agent in plain text. Never put a secret
  there; authenticate with the agent's own bearer secret on a handler you
  serve.

## Caller ID and numbers

- `caller_id="+1..."` sets what the far end sees on outbound calls and
  transfers. It must be a number on the account.
- Buying a number is billable: confirm country, area code and cost with the
  user first, then `client.phone_numbers.purchase_available(...)`. To use a
  number they already own, `import_()` it with their carrier's termination URI
  and `assign_agent()`.

## Webhooks

Subscribe to `session.completed` and `call.ended` to log outcomes, update a
CRM after the call, or trigger `voice-agent-call-review`. Verify every
delivery against the raw body with `verify()` before parsing, and make the
handler idempotent: deliveries can repeat.
