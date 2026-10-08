---
name: voice-agent-templates
description: Recipes for complete AssemblyAI voice agents that handle high-volume phone work - appointment booking, order status, a website FAQ line, a smart IVR that replaces press-1 menus, bill payments, pharmacy refills, appointment reminders and lead qualification. Use this when the user asks for one of those agents, or describes a phone job in plain words ("a receptionist for my dental practice", "a line that tells people where their order is"), before writing any code with the assemblyai-agents SDK.
---

# Voice agent templates

Each template is a whole agent for one phone job that is expensive to staff.
They share one shape: **your code is the brain.** A `decide(turn)` function
written in Python chooses every reply, calls a model only where judgement is
needed, and checks each step in code. The platform still owns speech, turn
taking, interruptions and the phone line.

`assemblyai-agents-sdk` is the API surface. This skill is what to build with it.

## Ask before you build

Every template depends on the user's own setup, and guessing it wastes a build.
Ask the template's setup questions first, in one short message, naming the
common choices so the user can answer in a word:

> Which calendar do you use: Google Calendar, Calendly, Cal.com or something else?

Then build with what they said. Until a credential exists, the tools return
demo data from a small dict at the top of the file, so the agent can be called
the same day. Say which secret to add and where it is read.

Ask nothing else up front. Voice, greeting wording and turn timing are cheap to
change after the first call.

## The shared brain

Start from `subagents.py` (stages, one model per stage) or `one_file_agent.py`
(one file) and keep this structure:

- **Stages in code.** A stage is a function of the transcript: identify the
  caller, collect what the job needs, act, confirm, close. `decide` picks the
  stage from what the conversation has established (`turn.result_of`,
  `turn.answer_following`), never from a counter you keep.
- **A fast model for words, a careful one for decisions.** Classifying intent
  and phrasing a settled answer want a small, fast model (a first token in
  well under a second). Choosing a tool and its arguments wants a stronger one.
  The AssemblyAI LLM Gateway (`https://llm-gateway.assemblyai.com/v1`,
  OpenAI-compatible, `Authorization: <ASSEMBLYAI_API_KEY>`) serves both, and
  `subagents.py` already reads `MODEL_BASE_URL` for it.
- **Policy lives in tools.** A tool refuses what the business would refuse:
  wrong caller, past cutoff, out of stock. The model cannot talk its way past a
  rule written in Python.
- **Read back before acting.** Every write (a booking, a payment link, a
  cancellation) is preceded by a spoken summary and a yes.
- **Fail into a person.** When a tool fails twice or the caller asks, transfer
  (`voice-agent-phone-features`) or take a message.

Ten seconds is the platform's ceiling for a reply, and the caller hears silence
while they pass. Get the first words out fast and do slow work in a tool.

## Templates

`references/templates.md` has each recipe: the setup questions, the stages,
the tools, and the phone features worth adding.

| Template | The job | Ask first |
| --- | --- | --- |
| Appointment booking | Book, move and cancel | Which calendar or booking system |
| Order status | Where is my order | Where orders live (Shopify, own API, ...) |
| Website FAQ | Answer from the business's own site | The website address |
| Smart IVR | Say what you need instead of pressing 1 | Which teams, and their numbers |
| Bill payments | Balance, due date, pay safely | Which billing system |
| Pharmacy refills | Request a refill, check if ready | Which pharmacy system |
| Appointment reminders | Outbound: confirm, cancel or move | Which calendar or booking system |
| Lead qualification | Ask, score, log, hand hot leads over | Which CRM |

Integrations for the systems named above are in `voice-agent-integrations`.

## Done means

- The setup questions were asked and answered, or demo data says so plainly.
- `decide` and every tool have unit tests, and one rehearsed call per stage
  runs offline (`starter/rehearse.py`).
- The README says which secrets to set and how to place a test call.
