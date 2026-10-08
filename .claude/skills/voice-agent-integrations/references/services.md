# Services

The one or two calls a voice agent usually needs from each service, with how
it authenticates and the trap that costs a call. Check the service's current
API reference before shipping: versions and plan limits change.

Secret names below are suggestions; tell the user whichever you use.

## Calendars

### Google Calendar
- **Auth:** a service account with the calendar shared to its email
  (`google_service_account_json`), or OAuth for a user's own calendar.
- **Free time:** `POST https://www.googleapis.com/calendar/v3/freeBusy` with
  `timeMin`, `timeMax`, `items: [{id: calendarId}]`; subtract busy blocks from
  opening hours in code.
- **Book:** `POST /calendar/v3/calendars/{calendarId}/events`.
- **Trap:** times are RFC 3339 with an offset. Store the business's time zone
  and convert the caller's "tomorrow at three" in code.

### Calendly
- **Auth:** personal access token, `Authorization: Bearer` (`calendly_token`).
- **Free time:** `GET https://api.calendly.com/event_type_available_times?event_type=<uri>&start_time=&end_time=`
  (a window of at most seven days).
- **Book:** depending on the plan, either book directly through Calendly's
  scheduling API or create a single-use link with `POST /scheduling_links` and
  text it to the caller.
- **Trap:** event types are URIs, not names. Look them up once with
  `GET /event_types?user=<uri>` and store them.

### Cal.com
- **Auth:** API key, `Authorization: Bearer` plus a `cal-api-version` header
  (`calcom_api_key`).
- **Free time:** `GET https://api.cal.com/v2/slots?eventTypeId=&start=&end=`.
- **Book:** `POST https://api.cal.com/v2/bookings` with the attendee's name,
  email or phone, and time zone.

## Commerce

### Shopify
- **Auth:** an Admin API access token from a custom app,
  `X-Shopify-Access-Token` (`shopify_token`), plus the shop domain.
- **Find an order:** `POST https://{shop}.myshopify.com/admin/api/{version}/graphql.json`
  with `orders(first: 1, query: "name:#1001")`, reading
  `displayFulfillmentStatus` and the fulfilment's tracking.
- **Trap:** order names carry a `#` prefix; callers never say it. Add it in
  code.

## CRMs

### HubSpot
- **Auth:** private app token, `Authorization: Bearer` (`hubspot_token`).
- **Find a contact:** `POST https://api.hubapi.com/crm/v3/objects/contacts/search`
  filtering `phone`.
- **Log a lead:** `POST /crm/v3/objects/contacts`, then a note or deal
  associated with it.

### Salesforce
- **Auth:** OAuth client credentials on a connected app; cache the access token
  until it expires (`salesforce_client_id`, `salesforce_client_secret`).
- **Create a lead:** `POST {instance_url}/services/data/v{version}/sobjects/Lead`.
- **Find by phone:** a SOQL query on `Contact` or `Lead`; normalise the number
  to E.164 on both sides.

## Payments

### Stripe
- **Auth:** a restricted secret key with only the permissions needed
  (`stripe_key`).
- **Take a payment safely:** create a Checkout Session or Payment Link and send
  the URL by SMS or email. Never take a card number by voice.
- **Read a balance:** `GET https://api.stripe.com/v1/invoices?customer=&status=open`.

## Help desks

### Zendesk
- **Auth:** `{email}/token:{api_token}` as basic auth (`zendesk_email`,
  `zendesk_token`).
- **Open a ticket:** `POST https://{subdomain}.zendesk.com/api/v2/tickets.json`
  with the caller's words as the description and the call's session id in a
  custom field, so the recording can be found later.

## Messaging

### Slack
- **Auth:** an incoming webhook URL (`slack_webhook_url`); it is itself a
  secret.
- **Post:** `POST {webhook_url}` with `{"text": "..."}`. Use it for "a caller
  needs a call back" with name, number and reason.

### Twilio SMS
- **Auth:** account SID and auth token as basic auth (`twilio_sid`,
  `twilio_token`).
- **Send:** `POST https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json`
  with `From`, `To`, `Body`. Confirm the number by reading it back first.

## Anything else

### A webhook
`POST` a JSON summary at the end of the call: caller, reason, outcome,
follow-up needed. Sign it with an HMAC so the receiver can verify it.

### Your own REST API
Ask how it is authenticated before writing the tool. A bearer token goes in a
secret; an API on a private network needs a public endpoint (or a small proxy)
the platform can reach. Map its response to the few fields the agent will say.
