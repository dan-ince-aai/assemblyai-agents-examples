---
name: voice-agent-integrations
description: Connect an AssemblyAI voice agent (assemblyai-agents SDK) to the systems a business runs on - calendars (Google Calendar, Calendly, Cal.com), commerce (Shopify), CRMs (HubSpot, Salesforce), payments (Stripe), help desks (Zendesk), messaging (Slack, Twilio SMS), a webhook, or any REST API. Use this when a voice agent's tool needs to read or write real data in another service, or when the user names one of these services.
---

# Integrations

An integration is a `@tool` whose body calls the service. The pattern is the
same for every service; `references/services.md` has the endpoint, auth and
gotchas for each.

## The pattern

```python
from assemblyai_agents import ToolContext, tool
from assemblyai_agents.replies import digits_said

DEMO_ORDERS = {"1001": {"status": "shipped", "eta": "Thursday"}}

@tool(timeout_seconds=8)
async def order_status(order_said: str, ctx: ToolContext = None) -> dict:
    """Look up an order by the number the caller read out.

    Args:
        order_said: The order number exactly as the caller said it.
    """
    number = digits_said(order_said)
    if not number:
        return {"found": False, "ask": "Ask the caller to read the order number again."}
    token = ctx.secret("shopify_token") if ctx else None
    if not token:
        order = DEMO_ORDERS.get(number)          # demo data until the secret exists
        return {"found": bool(order), **(order or {}), "demo": True}
    response = await ctx.http.post(SHOPIFY_GRAPHQL, headers={"X-Shopify-Access-Token": token}, json=...)
    ...
```

- **Take the caller's words, validate in the handler.** Models pass
  placeholders ("order number") and half-heard values. Return a readable
  refusal (`{"found": False, "ask": "..."}`), never raise.
- **Credentials are secrets, read per call.** `ctx.secret(name)` on a hosted
  tool, the environment on your own server. Never in source, the prompt, a
  pre-connect header or a tool URL. Tell the user the exact name to set.
- **Demo data until the secret exists**, labelled `"demo": True` so the agent
  never presents it as real. The agent can be called the day it is written.
- **Short timeouts.** The caller hears silence while a tool runs. Eight seconds
  is a lot; most lookups should be under two. Return a "try again" result on
  timeout rather than letting the platform's timeout fire.
- **Return what the agent will say, not the raw payload.** A few named fields
  keep the model from reading out an internal ID or a JSON blob.
- **Writes need a yes.** Read the change back and only act on an explicit
  confirmation; make the write idempotent (an idempotency key from the call's
  session id plus the action) so a retried tool call does not book twice.
- **Mock the service in tests.** `create_tool_context()` stubs `ctx.http`;
  assert the request you send as well as what you return.

## Choosing what to integrate

Ask the user which system holds the data before writing a tool: "Where do your
orders live: Shopify, WooCommerce, or your own API?" A guessed integration is
code they will delete. If they have no system, a Google Sheet or Airtable base
is a fine first store.
