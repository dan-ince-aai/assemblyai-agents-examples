# Template recipes

Each recipe lists the questions to ask before writing code, the stages `decide`
moves through, the tools, and the phone features that make it hold up on a real
line. Feature names refer to `voice-agent-phone-features` and
`voice-agent-speech`.

## Appointment booking

**Ask first:** which calendar or booking system (Google Calendar, Calendly,
Cal.com, Acuity, their own); the services offered and how long each takes;
opening hours and time zone.

**Stages:** identify the caller (name, and phone number if not on the line) →
what they want (book, move, cancel) → find a time → read it back → confirm →
close.

**Tools:**
- `find_slots(service, day_said)` returns up to three open times. Parse the
  day in code from the caller's words; never let the model invent a date.
- `book(service, start_iso, name, phone)` refuses a slot that has gone since it
  was offered and returns the next three instead.
- `find_booking(name, phone)` and `cancel_booking(booking_id)` or
  `move_booking(booking_id, start_iso)`.

**Phone features:** keyterms for service and staff names; a protected
greeting if the line is recorded; a cold transfer to the front desk.

## Order status

**Ask first:** where orders live (Shopify, WooCommerce, BigCommerce, their own
API); what an order number looks like; what counts as late.

**Stages:** get the order number → spell it back → look it up → say status and
delivery date → offer a person if late or missing.

**Tools:** `order_status(order_said)` takes the caller's words, normalises
digits with `digits_said`, and returns `{found, status, eta, carrier}`; a
not-found returns what to ask next rather than an error.

**Phone features:** pre-connect lookup of recent orders by caller number, so a
returning customer is never asked; keyterms for the order prefix.

## Website FAQ

**Ask first:** the website address; which pages matter most (hours, prices,
services, policies, contact); what to do with questions the site does not
answer (take a message, transfer, or both).

**Build step:** fetch the site *at build time*, not per call. Read the home
page, follow up to five same-site links that answer callers' questions, strip
the markup, and write the facts to `knowledge.md` in the project. Never invent
a price, hour or policy the pages do not state. Commit the file so a reviewer
can see what the agent knows.

**Stages:** answer from `knowledge.md` → if nothing matches, say so plainly and
take a message.

**Tools:** `search_knowledge(question)` returns the few relevant passages (a
keyword match is enough for a small site); `take_message(name, phone,
message)`.

**Refreshing:** a scheduled job re-runs the build step and opens a pull
request with the diff, so a changed price is reviewed before it is said.

## Smart IVR

Callers say what they need in their own words; the agent answers what it can
and routes the rest. It replaces a press-1 menu, so it must be faster than one.

**Ask first:** the teams to route to, each with its number and hours; the
questions the agent should answer itself; what happens out of hours.

**Stages:** one open question ("What can I help with today?") → classify into
a team or a self-serve answer → confirm in a few words ("Billing, one moment")
→ transfer, or answer and offer more help.

**Tools:** `route(team)` is the transfer target per team; `answer(topic)`
returns the approved wording for each self-serve topic.

**Brain:** classification is the fast model's job, with the team list and two
example phrasings per team in its prompt. A low-confidence result asks one
clarifying question, never a menu read aloud.

**Phone features:** one transfer target per team; keypad fallback ("or press 1
for billing") for callers who prefer it; a protected greeting.

## Bill payments

**Ask first:** which billing system (Stripe, Chargebee, Zuora, their own);
how a caller is verified (account number plus postcode is common); whether a
payment link by SMS or email is acceptable.

**Stages:** verify → read balance and due date → offer a payment link → send
it → confirm it was sent.

**Tools:** `verify_caller(account_said, postcode_said)`;
`balance(account_id)`; `send_payment_link(account_id, channel)`.

**Never take a card number by voice.** Send a link. If card entry on the call
is a hard requirement, collect it on the keypad with a sensitive profile
(`voice-agent-phone-features`) and pass it straight to the processor.

## Pharmacy refills

**Ask first:** which pharmacy system holds prescriptions; how a caller is
verified (name and date of birth is common); when refills are ready.

**Stages:** verify → take the prescription number → request the refill → say
when it will be ready → transfer any medical question to a pharmacist.

**Tools:** `verify_patient(name, dob_said)`; `request_refill(rx_said)`;
`refill_status(rx_said)`.

**Hard rule in code:** the agent gives no medical advice. A tool-level
classifier on the caller's words routes anything clinical to the pharmacist,
whatever the model wants to say.

## Appointment reminders (outbound)

**Ask first:** which calendar or booking system; when to call (the day before
is common) and the calling window; the voicemail wording.

**Placing the calls:** a scheduled job reads tomorrow's bookings and places one
call each with `client.calls.create`; the number calling out must have this
agent assigned.

**Stages:** say who is calling and why → confirm, cancel or move → update the
booking → close. On voicemail, leave the short message and end.

**Tools:** `booking_for_call()` reads the booking this call is about (pass the
booking id in through pre-connect, keyed on the dialled number);
`confirm`, `cancel`, `move`.

**Phone features:** voicemail handling; a protected greeting so the first line
lands on a noisy line.

## Lead qualification

**Ask first:** which CRM (HubSpot, Salesforce, Pipedrive, their own); the
qualifying questions and what makes a lead hot; who gets hot leads, and their
number.

**Stages:** one question at a time (company size, timeline, budget, need) →
score in code → log → transfer hot leads to sales, book a call for warm ones.

**Tools:** `log_lead(fields)`; `score(answers)` is plain Python, not the
model; `route_hot_lead()` is a warm transfer that briefs the rep.

**Phone features:** warm transfer with consult instructions; keyterms for the
product names callers will say.
