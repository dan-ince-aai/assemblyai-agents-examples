"""Serve the platform's requests from this project's functions.

    export PUBLIC_BASE_URL=https://<host> AGENT_SECRET=... BYO_LLM=1
    python backend.py

`agent.serve()` binds the declaration to PUBLIC_BASE_URL, deploys it (create,
or update the stored id), and answers every route the platform will call:

    POST /tools/{name}            the agent's tools
    POST /v1/chat/completions     reply.decide, streamed
    POST /pre-connect/lookup      before a phone call is answered
    POST /webhooks/voice-agents   verified against WEBHOOK_SECRET
    GET  /healthz

Run this where the host gives you an address (Railway, Render, a VM). For a
laptop, `run.py` gets one from ngrok first. For an ASGI host (Modal, Lambda),
`assemblyai_agents.serving.asgi(agent, secret=...)` is the same routes as an app.
"""

import os

from agent import agent

if __name__ == "__main__":
    agent.serve(
        secret=os.environ.get("AGENT_SECRET"),
        port=int(os.environ.get("PORT", "8000")),
        webhook_secret=os.environ.get("WEBHOOK_SECRET"),
        on_event=lambda event: print(f"[webhook] {event.get('event') or event.get('type')}", flush=True),
    )
