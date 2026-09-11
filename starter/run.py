"""Run this agent from a laptop: address, deploy, serve. One command.

    export ASSEMBLYAI_API_KEY=...
    python run.py

Gets a public address for this machine, then hands it to `agent.serve()`, which
binds the declaration to it, deploys, and answers the platform's requests until
you stop it. Point a phone number at the agent id it prints and call in.

The only file here that knows a tunnel exists is `expose.py`. Set
PUBLIC_BASE_URL and it starts nothing; on a real host, run `backend.py` instead
and there is no tunnel at all.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from expose import public_address

PORT = int(os.environ.get("PORT", "8000"))


def main() -> int:
    if not os.environ.get("ASSEMBLYAI_API_KEY"):
        sys.exit("set ASSEMBLYAI_API_KEY")
    os.environ.setdefault("AGENT_SECRET", "starter-secret")
    os.environ.setdefault("BYO_LLM", "1")

    with public_address(PORT) as base_url:
        # The declaration reads PUBLIC_BASE_URL when it is imported, so set it
        # before the import; agent.serve() then has nothing left to resolve.
        os.environ["PUBLIC_BASE_URL"] = base_url
        from agent import agent

        print(f"\nserving from {base_url}; Ctrl-C to stop\n", flush=True)
        agent.serve(
            secret=os.environ["AGENT_SECRET"],
            port=PORT,
            webhook_secret=os.environ.get("WEBHOOK_SECRET"),
            on_event=lambda event: print(f"[webhook] {event.get('event') or event.get('type')}"),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
