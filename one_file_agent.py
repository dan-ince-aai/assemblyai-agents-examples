"""One file, your own code, reachable over HTTP so a phone call works.

    export ASSEMBLYAI_API_KEY=...
    python one_file_agent.py

That deploys the agent, gets a public address for this process, and serves the
platform's requests from the functions below until you stop it. Point a phone
number at the agent id it prints and a real caller gets the same code: the tools
are HTTP tools, so nothing depends on a client being connected.

The two things you write are in this file and nowhere else:

* `@tool` functions, whose bodies can be anything Python can do. Query Chroma,
  call an internal API, read a database, run whatever logic you like.
* `decide(turn)`, which chooses what the agent says next. Leave it out and the
  platform's own model runs the conversation instead.

There is no backend to write and no framework to install. `serve()` answers the
platform from the declaration; `expose.py` gets this process an address, and is
the part that goes away once there is somewhere to deploy to.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assemblyai_agents import VoiceAgent, tool
from assemblyai_agents.replies import Turn, call_tool, digits_said, say, silence

from expose import public_address

PORT = int(os.environ.get("PORT", "8000"))
# Presented by the platform on every request to this process, and checked by
# `serve`. Anything that reaches the address otherwise gets a 401.
SECRET = os.environ.get("SHARED_SECRET", "change-me-" + os.urandom(4).hex())

# Stand in for whatever you would really query.
ORDERS = {
    "1042": {"status": "out for delivery", "eta": "before six this evening"},
    "1043": {"status": "packed", "eta": "tomorrow morning"},
}


# --------------------------------------------------------------------------- your tools


@tool(timeout_seconds=10)
async def order_status(order_said: str) -> dict:
    """Look up an order by the number the caller read out.

    Args:
        order_said: The order number exactly as the caller said it.
    """
    # The caller's words come in; the reading happens here, because the platform
    # refuses a tool argument whose value the conversation never established.
    number = digits_said(order_said)[:4]
    found = ORDERS.get(number)
    print(f"  [tool] order_status({order_said!r}) -> {number} {'found' if found else 'unknown'}", flush=True)
    if not found:
        return {"found": False, "number": number}
    return {"found": True, "number": number, **found}


@tool(timeout_seconds=10)
async def leave_message(name: str, message: str) -> dict:
    """Take a message for the team.

    Args:
        name: The caller's name.
        message: What they want passed on.
    """
    print(f"  [tool] leave_message({name!r}, {message!r})", flush=True)
    # Any code at all: append to a queue, insert a row, post to Slack.
    return {"taken": True, "name": name}


TOOLS = [order_status, leave_message]


# --------------------------------------------------------------------------- what it says
#
# Plain Python. The scripted lines cannot drift, the branches are yours, and
# anything you would rather a model handled can call one from here.

GREETING = "Thanks for calling Northwind. Do you have an order number for me?"
ASK_NUMBER = "Could you read me the four digit order number?"
ASK_NAME = "No problem. Can I take your name and a message for the team?"


def decide(turn: Turn):
    pending = turn.pending

    if pending and pending.name == "order_status":
        if pending.get("found"):
            spoken = " ".join(str(pending.get("number")))
            return say(
                f"Order {spoken} is {pending.get('status')}, expected {pending.get('eta')}. "
                f"Anything else?"
            )
        return say(f"I cannot find that one. {ASK_NUMBER}")

    if pending and pending.name == "leave_message":
        return say(f"Thank you, I have passed that on. Goodbye.")

    said = turn.caller_said
    if not said:
        return say(ASK_NUMBER)

    if turn.said_before("I have passed that on"):
        return silence()  # the call is done; an agent cannot hang up

    if len(digits_said(said)) >= 4:
        return call_tool("order_status", order_said=said)

    if turn.said_before(ASK_NAME):
        # Their own words, so the platform accepts them as established values.
        return call_tool("leave_message", name=said, message=said)

    if any(word in said.lower() for word in ("no", "don't have", "lost", "cannot find")):
        return say(ASK_NAME)

    return say(ASK_NUMBER)


# --------------------------------------------------------------------------- wiring


# --------------------------------------------------------------------------- the agent

agent = VoiceAgent(
    name="Northwind order line",
    voice=os.environ.get("VOICE", "alba"),
    system_prompt="You answer order questions for Northwind. Keep replies short.",
    greeting=GREETING,
    tools=TOOLS,
    # This process decides every reply. Remove the line and the platform's own
    # model runs the conversation instead, still calling the same tools.
    reply=decide,
)


def main() -> int:
    if not os.environ.get("ASSEMBLYAI_API_KEY"):
        sys.exit("set ASSEMBLYAI_API_KEY")
    with public_address(PORT) as base_url:
        # Every tool call and every reply arrives here over HTTPS, whether the
        # caller is on a phone or in a browser. Blocks.
        agent.serve(public_url=base_url, secret=SECRET, port=PORT, id_file=".one_file_agent_id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
