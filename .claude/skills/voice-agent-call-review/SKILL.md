---
name: voice-agent-call-review
description: Review real calls to an AssemblyAI voice agent and improve it - pull recent sessions and their timelines with the assemblyai-agents SDK, find where calls went wrong (misheard words, slow replies, interruptions, failed tools, early hang-ups), spot patterns across calls, turn calls into offline test scenarios, and fix the agent's code. Use this when the user asks how their agent is doing, why calls fail, wants to "find issues and fix them", make the agent faster, or build tests from real calls.
---

# Reviewing calls

The fastest way to improve a voice agent is to read what happened on its real
calls. Every completed session has three artifacts: an `audio` recording, a
`timeline` (every turn, with what triggered it, the transcript, tool calls and
timings) and `metadata`.

## Pull the calls

```bash
python .claude/skills/voice-agent-call-review/scripts/pull_calls.py AGENT_ID --limit 20
```

This writes `calls/<session>.json` and `calls/summary.md`. Read the summary
first, then open the sessions it points at.

Calls contain what callers said: names, numbers, sometimes health or payment
details. Keep `calls/` out of version control, never paste a transcript into a
test or a commit, and delete the folder when the review is done.

## What to look for

Read each problem call turn by turn, and name the cause before changing code.

| Symptom in the timeline | Usual cause | Fix |
| --- | --- | --- |
| A name, code or number transcribed wrong | The word is unknown to the recogniser | `keyterms`, `transcription_prompt`, read-back (`voice-agent-speech`) |
| `time_to_first_audio_ms` over 1500 | A slow tool, a long prompt, or a slow model before the first words | Shorter tool timeouts, a filler line before slow work, a faster model for wording |
| `interrupted_at_ms` on many agent turns | Replies too long, or silence thresholds too short | Shorter replies; raise `min_silence` |
| The caller repeats themselves | The agent asked again for something it had | Read it back from the transcript (`turn.result_of`, `turn.answer_following`) |
| A tool call with no result, or prose where JSON was expected | The tool failed, timed out or was refused | Fix the tool; check `pending.ran` in `decide` |
| The call ends early with a short close | The caller gave up | Find the turn before; usually a loop or a wrong answer |
| The agent says it cannot access the system | Your tool's host was unreachable | Your server log, then the timeline's tool entry |

## Then

1. **Summarise before fixing.** What callers wanted, whether they got it, and
   the three changes that would help most, with the session ids that show each.
   Ask the user before a change that alters what the agent says or does.
2. **Turn calls into tests.** For each call that went wrong, write an offline
   scenario (`starter/rehearse.py`): the caller's goal, their lines
   paraphrased with invented details, and what the agent must do. The test
   fails before the fix and passes after.
3. **Fix the code**, run the tests, redeploy, and compare the next batch of
   calls with this one.

## Patterns across calls

With twenty or more calls, count rather than read: the most common requests
(is there a missing tool?), questions the agent could not answer (is there
missing knowledge?), and the stage where callers drop off. A request that
appears in one call in five deserves its own path through `decide`.
