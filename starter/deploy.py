"""Deploy without serving, or inspect and remove the deployed agent.

    export ASSEMBLYAI_API_KEY=... PUBLIC_BASE_URL=https://<host> AGENT_SECRET=... BYO_LLM=1
    python deploy.py                   create, or update the stored id
    python deploy.py --show            read the deployed agent back
    python deploy.py --delete          remove it and forget the id

`agent.serve()` already deploys before it serves, so this is for a CI step or a
host where the process that serves is not the one that deploys. The id is kept
in .agent_id next to this file, per host, so re-running never leaves a second
copy behind.
"""

import argparse
import os
import sys

from assemblyai_agents import Client, NotFoundError
from assemblyai_agents.deploy import id_file_for, stored_agent_id

from agent import agent

BASE_URL = os.environ.get("AAI_BASE_URL", "https://agents.assemblyai.com").rstrip("/")
ID_FILE = id_file_for(".agent_id", BASE_URL)


def describe(deployed) -> str:
    lines = [f"{deployed.id}  {deployed.name!r}  voice={deployed.voice.voice_id}"]
    for tool in deployed.tools or []:
        keypad = ", ".join(p.parameter_name for p in tool.dtmf_collected_arguments or [])
        lines.append(f"  {tool.name:22} {tool.timeout_seconds:>4}s  {tool.http.url if tool.http else '-'}"
                     + (f"  keypad: {keypad}" if keypad else ""))
    for entry in deployed.pre_connect_requests or []:
        lines.append(f"  pre-connect  {entry.http.url}  overrides={entry.allow_overrides}")
    for llm in deployed.llm or []:
        lines.append(f"  replies from {llm.base_url}  model={llm.model}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()

    client = Client(base_url=BASE_URL)
    agent_id = stored_agent_id(None, ID_FILE)
    print(f"host {BASE_URL}  (id file {ID_FILE.name})")

    if args.show:
        if not agent_id:
            print("nothing deployed yet")
            return 1
        print(describe(client.agents.get(agent_id)))
        return 0

    if args.delete:
        if not agent_id:
            print("nothing deployed yet")
            return 0
        try:
            client.agents.delete(agent_id)
            print(f"deleted {agent_id}")
        except NotFoundError:
            print(f"{agent_id} was already gone")
        ID_FILE.unlink(missing_ok=True)
        return 0

    deployed_id = agent.deploy(client=client)      # PUBLIC_BASE_URL and AGENT_SECRET from the environment
    print(describe(client.agents.get(deployed_id)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
