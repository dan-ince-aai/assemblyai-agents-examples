"""The agent: its tools, and the one declaration that deploys them.

Nothing here touches the network at import time, so the tests, the backend and
the deploy script can all import it.

Environment:
    PUBLIC_BASE_URL   public HTTPS address of this process (a tunnel in development)
    AGENT_SECRET      shared secret the platform presents on every request here
    BYO_LLM=1         reply.py decides every reply; unset, the platform's model talks
    AGENT_NAME        the name the agent gives (default "Sam")
    VOICE             a voice id (default "alba")
"""

import os

from assemblyai_agents import Captured, PreConnectRequest, VoiceAgent, tool

import reply
import store

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or None
AGENT_SECRET = os.environ.get("AGENT_SECRET") or None
AGENT_NAME = os.environ.get("AGENT_NAME", "Sam")
VOICE = os.environ.get("VOICE", "alba")
# Treat any caller as the demo patient, so a call from any handset reaches the
# personalised greeting. Off by default.
DEMO_MATCH_ANY = os.environ.get("DEMO_MATCH_ANY", "") not in ("", "0", "false")



# --------------------------------------------------------------------------- tools
#
# Two habits worth keeping, both learned from the platform refusing things:
#
# 1. Take the caller's words, not a value you derived from them. The platform
#    checks every argument against the conversation and refuses a call carrying
#    anything nobody said, so the reading belongs at this end.
# 2. Return what you read back. Whatever writes the reply sees the tool result
#    and nothing else, so a result that omits the id cannot name it out loud.


@tool(timeout_seconds=8)
async def find_patient(reference_said: str) -> dict:
    """Find the patient record from the reference number on their reminder.

    Returns nothing identifying: the caller states their own name and
    verify_caller checks it.

    Args:
        reference_said: The reference as the caller read it out, in their words.
    """
    patient = store.find_by_reference(reference_said)
    if patient is None:
        return {"found": False}
    return {"found": True, "reference": patient["reference"], "last_seen": patient["last_seen"]}


@tool(timeout_seconds=8)
async def verify_caller(caller_said: str, reference: str = "") -> dict:
    """Check the name the caller gave against the name on the record.

    Pass exactly what the caller said, however they said it. Omit reference
    when they have not read one out: the record matched from the number they
    called from is used instead.

    Args:
        caller_said: Exactly what the caller said, word for word.
        reference: The patient reference, if the call has established one.
    """
    patient = store.resolve(reference)
    if patient is None:
        return {"verified": False, "problem": "no_record_in_context"}
    heard = store.extract_name(caller_said)
    if not heard:
        # They asked something rather than answering. No attempt is spent and
        # nothing is implied about their name.
        return {"verified": False, "problem": "no_name_heard"}
    if not store.name_matches(patient, heard):
        return {"verified": False, "problem": "no_match", "name_heard": heard}
    return {
        "verified": True,
        "reference": patient["reference"],
        "first_name": patient["first_name"],
        "balance_due": patient["balance_due"],
    }


@tool(timeout_seconds=8)
async def find_appointments(preference_said: str = "") -> dict:
    """List the next free appointments, soonest first.

    Args:
        preference_said: What the caller said about when they would like to come in, if anything.
    """
    slots = store.open_slots(limit=4)
    return {
        "slots": [
            {**slot, "spoken": f"{store.spoken_date(slot['date'])} at {store.spoken_time(slot['time'])}"}
            for slot in slots
        ],
        "preference_noted": preference_said or None,
    }


@tool(timeout_seconds=10)
async def book_appointment(slot_date: str, slot_time: str, reference: str = "") -> dict:
    """Book one of the free appointments for this patient.

    Use a date and time exactly as find_appointments returned them.

    Args:
        slot_date: The appointment date, as YYYY-MM-DD.
        slot_time: The appointment time, as HH:MM.
        reference: The patient reference, if the call has established one.
    """
    patient = store.resolve(reference)
    if patient is None:
        return {"booked": False, "problem": "no_record_in_context"}
    result = store.book(patient, slot_date, slot_time)
    if result.get("booked"):
        result["spoken"] = f"{store.spoken_date(slot_date)} at {store.spoken_time(slot_time)}"
    return result


@tool(timeout_seconds=10)
async def request_callback(reason: str, note: str = "", reference: str = "") -> dict:
    """Ask a member of the practice team to call this patient back.

    Args:
        reason: Why a person needs to call, in a few words.
        note: Anything the caller said that the team should see.
        reference: The patient reference, if the call has established one.
    """
    return store.request_callback(store.resolve(reference), reason, note)


TOOLS = [find_patient, verify_caller, find_appointments, book_appointment, request_callback]


# --------------------------------------------------------------------------- the declaration
#
# The prompt is short on purpose. With `llm=` set, reply.py decides every word,
# so the prompt is only what the platform prepends to what your endpoint sees.

SYSTEM_PROMPT = f"""
You are {AGENT_NAME}, on the phone for {store.PRACTICE}, on a recorded line.
Keep every reply to one or two short sentences and ask one question at a time.
Confirm who you are speaking to before discussing anything on their record.
"""


# --------------------------------------------------------------------------- pre-connect
#
# Runs before a phone call is answered, from this process. Telephony only: a
# WebSocket session never runs it and the flow falls back to asking for the
# reference. It fails open, so a slow lookup costs the personalised greeting and
# nothing else.

# The platform's pre-connect request arrived with an empty body on a live call,
# so there was no caller number in it to look up. Every plausible field is
# checked anyway, and the lookup fails open.
CALLER_KEYS = ("from", "from_number", "caller", "caller_id", "ani", "phone_number")


def caller_number(payload: dict) -> str | None:
    for key in CALLER_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    for value in payload.values():
        if isinstance(value, dict):
            found = caller_number(value)
            if found:
                return found
    return None


def lookup(payload: dict) -> dict:
    """Find the caller before the call is answered, and greet them by name.

    Says nothing from their record: nobody has confirmed who picked up yet.
    """
    number = caller_number(payload) or os.environ.get("DEMO_CALLER_NUMBER", "")
    patient = store.find_by_phone(number) if number else None
    if patient is None and DEMO_MATCH_ANY:
        patient = next(iter(store.PATIENTS.values()))
    store.remember_in_flight(patient)
    reply.memo.forget()  # a new call starts with nothing remembered
    if patient is None:
        return {"matched": False}
    return {
        "matched": True,
        "reference": patient["reference"],
        "first_name": patient["first_name"],
        "greeting": (
            f"Thank you for calling {store.PRACTICE} on a recorded line. My name is "
            f"{AGENT_NAME}. I have found your record from the number you are calling "
            f"from. Could you give me your full name so I can check it?"
        ),
    }


# --------------------------------------------------------------------------- the declaration
#
# No URLs anywhere. The tools and the pre-connect handler are served by this
# process, and `reply.decide` decides every word when BYO_LLM is set. The
# address the platform reaches all of that at is bound when the agent is
# deployed — from PUBLIC_BASE_URL here, or from whatever `agent.serve()` is
# given.

SYSTEM_PROMPT = f"""
You are {AGENT_NAME}, on the phone for {store.PRACTICE}, on a recorded line.
Keep every reply to one or two short sentences and ask one question at a time.
Confirm who you are speaking to before discussing anything on their record.
"""

agent = VoiceAgent(
    name=f"{store.PRACTICE} reception",
    voice=VOICE,
    system_prompt=SYSTEM_PROMPT,
    greeting=(
        f"Thank you for calling {store.PRACTICE} on a recorded line. "
        f"My name is {AGENT_NAME}. How can I help?"
    ),
    tools=TOOLS,
    reply=reply.decide if os.environ.get("BYO_LLM") else None,
    pre_connect=[
        PreConnectRequest(
            handler=lookup,
            returns=[
                Captured(name="reference", path="reference", default=""),
                Captured(name="first_name", path="first_name", default=""),
            ],
            timeout_ms=800,
            allow_overrides=True,
        )
    ],
    public_url=PUBLIC_BASE_URL,
    secret=AGENT_SECRET,
)
