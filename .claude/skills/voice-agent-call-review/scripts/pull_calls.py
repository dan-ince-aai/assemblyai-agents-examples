"""Download an agent's recent calls for review.

    python pull_calls.py AGENT_ID [--limit 20] [--out calls]

Writes one JSON file per completed session (its metadata and timeline) and a
summary.md with the numbers worth looking at first: close reasons, slow
replies, interruptions and tool calls. Reads ASSEMBLYAI_API_KEY; set
ASSEMBLYAI_BASE_URL for the US host.

Calls carry what callers said. Keep the output out of version control and
delete it when the review is done.
"""

import argparse
import json
import os
import statistics
from pathlib import Path

import httpx

from assemblyai_agents import Client

SLOW_MS = 1500


def timeline_of(session) -> dict:
    for artifact in session.artifacts or []:
        if artifact.type == "timeline":
            return httpx.get(artifact.url, timeout=30).json()
    return {}


def summarise(session, timeline: dict) -> dict:
    turns = timeline.get("turns") or []
    first_audio = [t["time_to_first_audio_ms"] for t in turns if t.get("time_to_first_audio_ms")]
    return {
        "id": session.id,
        "duration_seconds": session.duration_seconds,
        "close_reason": session.public_close_reason,
        "turns": len(turns),
        "interrupted": sum(1 for t in turns if t.get("interrupted_at_ms") is not None),
        "slow_replies": sum(1 for ms in first_audio if ms > SLOW_MS),
        "median_first_audio_ms": int(statistics.median(first_audio)) if first_audio else None,
        "tools": [call.get("name") for t in turns for call in t.get("tool_calls") or []],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", default="calls")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    client = Client(base_url=os.environ.get("ASSEMBLYAI_BASE_URL", "https://agents.assemblyai.com"))

    rows = []
    for listed in client.sessions.list(agent_id=args.agent_id, status="completed", limit=args.limit):
        if len(rows) >= args.limit:
            break
        session = client.sessions.get(listed.id)
        timeline = timeline_of(session)
        (out / f"{session.id}.json").write_text(
            json.dumps({"session": session.model_dump(mode="json"), "timeline": timeline}, indent=2)
        )
        rows.append(summarise(session, timeline))

    lines = [
        f"# {len(rows)} calls to {args.agent_id}",
        "",
        "| session | seconds | close reason | turns | interrupted | slow (>1.5 s) | median first audio | tools |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['duration_seconds']} | {row['close_reason']} | {row['turns']} "
            f"| {row['interrupted']} | {row['slow_replies']} | {row['median_first_audio_ms']} "
            f"| {', '.join(t for t in row['tools'] if t) or '-'} |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {len(rows)} calls and summary.md to {out}/")


if __name__ == "__main__":
    main()
