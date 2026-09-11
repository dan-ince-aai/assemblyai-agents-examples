# `assemblyai-agents` API reference (v0.2)

Top-level exports of `assemblyai_agents`: `Client`, `AsyncClient`, `VoiceAgent`,
`tool`, `Tool`, `ToolContext`, `deploy`, `AudioFormat`, `AudioInput`,
`AudioOutput`, `HumanTransfer`, `PreConnectRequest`, `Header`, `Captured`,
`AgentConnection`, `AsyncRealtimeSession`, `UnknownEvent`, the WebSocket event
models, `verify`, the exceptions, the audio helpers, and five request models
(`AgentCreateRequest`, `AgentUpdateRequest`, `LlmConfigRequest`,
`PlaintextToolDefinition`, `VoiceConfig`). Everything else in
`assemblyai_agents.models.rest`. Serving is `assemblyai_agents.serving`; reply
writing is `assemblyai_agents.replies`.

## Install

```bash
pip install "git+https://github.com/dan-ince-aai/assemblyai-agents-python.git"
pip install "assemblyai-agents[audio] @ git+https://github.com/dan-ince-aai/assemblyai-agents-python.git"   # mic/speakers, needs PortAudio
```
Python ≥ 3.11. httpx, pydantic v2, websockets.

## VoiceAgent

```python
VoiceAgent(*, name: str, system_prompt: str, voice: str,
           greeting: str | None = None,
           reply: Callable[[Turn], Say | Call | Silence] | None = None,
           input: AudioInput | None = None, output: AudioOutput | None = None,
           tools: list[Tool] | None = None,
           transfer_targets: list[HumanTransfer] | None = None,
           pre_connect: list[PreConnectRequest] | None = None,
           outbound_trunk_id: str | None = None, caller_id: str | None = None,
           public_url: str | None = None, secret: str | None = None,
           llm: LlmConfigRequest | None = None)          # deprecated
```
- Frozen, keyword-only, cannot be subclassed. `system_prompt` dedented + stripped.
- **Two modes.** No `reply` → the platform's model talks. `reply=` → your
  function decides every turn; the wire's `llm` block is derived
  (`base_url={public_url}/v1`, `model=<slug of name>`, `api_key=secret`).
  `llm=` is deprecated and refused together with `reply=`.
- **Address.** Anything hosted here — a bare tool, a `handler=` pre-connect,
  `reply` — needs `public_url` (https). Set it here, or bind with
  `agent.hosted_at(public_url, secret=...)` (returns a copy), or let
  `serve()`/`deploy()` do it from `public_url=` / `PUBLIC_BASE_URL`.
  `to_request()` on an unbound hosting agent raises `ConfigurationError`.
- `secret` becomes `Authorization: Bearer <secret>` on every hosted tool and
  pre-connect, and the reply endpoint's key. `repr=False`.
- Properties/methods: `hosts_replies`, `needs_address`, `hosted_tool_names()`,
  `hosted_pre_connect_paths()`, `hosted_at(url, *, secret=None)`,
  `to_request() -> AgentCreateRequest`, `to_update_request()` (whole
  declaration; PUT replaces), `tool_definitions()`, `pre_connect_requests()`,
  `wire_transfer_targets()`, `deploy(**kw) -> str`, `serve(**kw)`.
- Checks at construction: unique tool names; ≤2 pre-connect, `sends` only
  earlier captures, unique capture names; transfers need `outbound_trunk_id`;
  `caller_id` E.164; `reply` callable; `public_url` https.
- `voice`: the API accepts `alba anna charles estelle eve george giovanni iris
  jane jean juergen lola mary michael paul rafael reid vera`; anything else is
  a 422 listing them. Wire: `VoiceConfig(voice_id=voice)`.

## @tool

```python
@tool
@tool(timeout_seconds=120, execution_mode=None, response_instructions=None,
      dtmf_collected_arguments=None,
      url=None, http_method=None, headers=None,      # a service you already run
      http=None)                                     # deprecated spelling of url=
def name(param: T, ...) -> R: """Description.\n\nArgs:\n    param: text"""
```
- Bare → **hosted by this process** (`tool.hosted is True`, `spec.http is None`);
  the deploy binds `{public_url}/tools/{name}` with the bearer header.
- `url=` → `PlaintextHttpToolConfig(url, http_method or POST, headers)`;
  `http_method=`/`headers=` without `url=` is refused.
- Rules (all `ConfigurationError` at import): snake_case; not a platform tool
  name; docstring first paragraph; every parameter typed (`str int float bool
  list[T] dict[str,T] Literal Enum Optional BaseModel`); return annotation
  JSON-serialisable; `timeout_seconds` 1–300; `hold` refused; no `*args`.
- `Tool`: `.name .spec .target .hosted`, `.definition() -> PlaintextToolDefinition`,
  `.hosted_at(url, *, http_method=None, headers=None) -> Tool` (a bound copy),
  `await .invoke(context=None, **arguments)` (sync targets run in a thread),
  `tool(...)` calls the raw function.
- `ToolContext` (Protocol): `http`, `log`, `session_id`, `aborted`, `secret(name)`.
  Declare `ctx: ToolContext = None`. Only the testing double implements it.
- `dtmf_collected_arguments`: `DtmfCollectionProfile(parameter_name, prompt,
  min_digits, max_digits, sensitive, terminator="#", confirm=None,
  timeout_seconds=None, escalate_hotkey_disabled=None)`. `sensitive` must be
  stated. Phone only; refuses WebSocket sessions.

## serving

```python
from assemblyai_agents.serving import serve, asgi, routes, claim_port, Refused, serve_agent

agent.serve(*, public_url=None, secret=None, host="0.0.0.0", port=None,      # port: PORT env, then 8000
            deploy=True, client=None, agent_id=None, id_file=".agent_id",
            webhook_secret=None, on_event=None, log=print, background=False)
```
`agent.serve()` = resolve address (`public_url` / `PUBLIC_BASE_URL`) and secret
(`secret` / `AGENT_SECRET`, else minted) → `claim_port` → `deploy` → `serve`.

```python
serve(agent, *, secret=None, host="0.0.0.0", port=None, webhook_secret=None, on_event=None,
      log=print, background=False, reply=None, pre_connect=None, tool_secret=None, llm_key=None)
asgi(agent, *, secret=None, webhook_secret=None, on_event=None, log=print, reply=None, pre_connect=None) -> ASGI app
routes(agent, ...) -> {(method, compiled_path): handler}     # handler(path, query, body_bytes, headers) -> (status, payload)
claim_port(host="0.0.0.0", port=8000)                        # OSError with the culprit if taken
Refused(status, detail)                                      # raise from a handler → that status
```
Routes: `POST /tools/{name}` (hosted tools only; 404 for a `url=` tool),
`POST /v1/chat/completions` (when `agent.reply`; SSE), `POST /pre-connect/{name}`
(each `handler=`), `POST /webhooks/voice-agents` (verified), `GET /healthz`.
All bearer-checked against `secret`. `tool_secret`/`llm_key`/`reply=`/
`pre_connect=` on `serve()` are deprecated aliases. `asgi()` runs handlers in a
worker thread and streams SSE frame by frame; answers lifespan.

## deploy

```python
from assemblyai_agents import deploy
deploy(agent, *, public_url=None, secret=None, client=None, agent_id=None, id_file=".agent_id", log=print) -> str
```
Binds, then `agents.update(stored_id)` or `agents.create()`; a vanished id is
recreated and overwritten. Id lookup order: `agent_id`, `AGENT_ID`, the id
file (suffixed `.<host>` on a non-default host). `resolve_public_url()`,
`resolve_secret()`, `id_file_for()`, `stored_agent_id()` are importable.

## replies

```python
from assemblyai_agents.replies import Turn, ToolResult, Say, Silence, Call, say, silence, call_tool, established, stream, json_body, digits_said, PRE_CONNECT_TOOL
```
- `Turn.from_request(body)`: `.request .messages .tool_names .caller_said .spoken
  .preconnect .pending .results`; `.said_before(marker)`, `.answer_following(fragment)`,
  `.result_of(name, arguments=None)`, `.has(tool)`.
- `ToolResult`: `.name .arguments .value .ran .note`, `.get(k)`, `.keypad_incomplete`.
- `say(text)`, `silence()`, `call_tool(name, **args)` (drops `None`/`""`),
  `established(**args)`, `stream(turn, answer, chunk_words=True)` (SSE lines),
  `json_body(turn, answer)`, `digits_said(text)`.

## Audio config

```python
AudioFormat(*, encoding="audio/pcm"|"audio/pcmu"|"audio/pcma", sample_rate: 24000|None)   # rate only with pcm
AudioInput(*, format, keyterms (≤100), transcription_mode "balanced"|"min_latency"|"max_accuracy",
           continuous_partials, transcription_prompt (≤1750), language_codes, voice_focus "near-field"|"far-field",
           voice_focus_threshold 0–1, extra: dict)
AudioOutput(*, format, volume 0–100, extra)
```
Always emit `type: audio`. Turn detection via `extra={"turn_detection": {"min_silence": 1000, "max_silence": 3000, "interrupt_response": True, "interruption_delay": None, "vad_threshold": 0.5}}`. `extra` refuses modelled keys. Voice is on the agent, never in `AudioOutput`.

## Telephony

```python
HumanTransfer(*, name, phone_number (E.164), mode="cold"|"warm", ring_timeout 1–600, consult_instructions, consult_timeout, record_consult)   # consult_* warm only; needs outbound_trunk_id
PreConnectRequest(*, handler=None | url=None (https), method="POST", headers: list[Header], sends, returns: list[Captured], timeout_ms 1–800, allow_overrides: bool=False)
Header(*, name, value)             # value required
Captured(*, name, path, default=None)   # dotted path, e.g. customer.tier
```
`handler=` → served at `.path` = `/pre-connect/{handler.__name__}`; `.hosted_at(public_url, secret=)` binds url + bearer. `allow_overrides=True` ⇒ wire `["greeting"]`. Fails open; top-level `greeting`/`reject` in the response.

## Clients and resources

```python
Client(api_key=None, *, base_url="https://agents.assemblyai.com", timeout=30.0, max_retries=3, transport=None); AsyncClient(...)
```
Resources: `agents` (`create(VoiceAgent|AgentCreateRequest)`, `get`, `list(limit, cursor)`, `update(id, VoiceAgent|AgentUpdateRequest)` — PUT replaces, `delete`); `sessions` (`list(limit, cursor, status, agent_id)`, `get(id)` → `artifacts[]` of `audio|timeline|metadata` presigned URLs, `delete`, async-only `connect(token=, url=, open_timeout=15.0, auto_resume=False, max_resume_attempts=5)`); `calls` (`list(limit, cursor, status: CallStatus, direction: CallDirection)`, `create(CreateCallRequest(from_number, to_number))` idempotent, `get`, `delete`); `phone_numbers` (`list`, `purchase_available(PurchaseAvailablePhoneNumberRequest(country_code, number_type: NumberType, area_code, locality, label, agent_id))` billable idempotent, `purchase(PurchasePhoneNumberRequest(phone_number))`, `import_(ImportPhoneNumberRequest(phone_number, termination_uri))`, `get(number)`, `deregister(number)`, `assign_agent(number, PhoneNumberAssignAgentRequest(agent_id))` (the `agent=` kwarg is a deprecated no-op), `unassign_agent(number)`); `tokens` (`create(TokenCreateRequest(expires_in_seconds=60))`); `webhooks` (`create(CreateWebhookSubscriptionRequest(url, events: list[WebhookEvent], secret ≥32, agent_id, enabled))`, `list(limit, cursor, include_disabled)`, `get`, `update(id, UpdateWebhookSubscriptionRequest)`, `delete`, `list_deliveries(session_id)`, `list_latest_deliveries(session_id)`); `builtin_tools.list()`.
Escape hatch: `client.request(method, path, *, params, json, headers, idempotent, timeout)`; `request_raw()` → `RawResponse`. Retries: 408, 429, 5xx, 409 `idempotency_in_progress`, transport errors. Pagers iterate or `next_page()`/`has_more`.

Enums: `HttpMethod GET POST PUT PATCH DELETE`; `ExecutionMode interactive hold`; `NumberType local mobile national`; `CallStatus dialing active ended failed refused`; `CallDirection inbound outbound`; `TransferMode cold warm`; `WebhookEvent session.started session.completed call.connected call.ended call.failed`; `DeliveryStatus pending delivered failed`.

## Realtime (a test client)

```python
AgentConnection(*, agent_id, api_key=None, client=None, audio=True, auto_resume=True, url=None, token=None)
```
`async with conn:` mints a token, connects, binds the agent. `await conn.run()`. Callbacks (decorator or call): `on_ready(SessionReady)`, `on_user_transcript(str)`, `on_agent_transcript(str)`, `on_agent_delta(str)`, `on_agent_audio(ReplyAudio)` (when `audio=False`), `on_error(SessionError)`. `conn.say(text)` sends a `conversation.message` the platform does not put in the transcript. `conn.session` is the `AsyncRealtimeSession`. **No tools run here**: a stray `tool.call` is answered with an error. A bad `agent_id` surfaces as `on_error(SessionError(code=agent_not_found))` then 1008. A DTMF agent refuses the session (1008 `invalid_value`).

`AsyncRealtimeSession`: `update(*, agent_id=, system_prompt=, greeting=, input=, output=, tools=, webhook=)`, `send_audio(bytes)`, `send_tool_result(call_id, result, *, is_error=False)`, `send_message(content, *, role="user")`, `create_reply(instructions=None)`, `cancel_reply(reply_id)`, `resume(session_id)`, `end()`, `close()`, `async for event in session`, `close_code`. Events: `SessionReady(session_id, resume_token, expires_at, config)`, `SessionUpdatedEvent`, `SessionError(code, message, param)`, `SessionEnded`, `InputSpeechStarted/Stopped`, `ReplyStarted/Audio/Done(status completed|interrupted)`, `ToolCall(call_id, name, arguments)`, `TranscriptUser/Agent/AgentDelta`, `UnknownEvent`. Audio: 16-bit LE mono PCM 24 kHz; helpers `pcm_to_base64 base64_to_pcm pcm16_to_ulaw ulaw_to_pcm16 pcm16_to_alaw alaw_to_pcm16`; `microphone_stream(session)`, `PlaybackSink()` with the `[audio]` extra.

## Webhooks

`verify(payload: bytes, signature_header: str, secret: str, *, tolerance=300, now=None) -> dict`. Header `t=<unix>,v1=<hex HMAC-SHA256(secret, f"{t}." + raw_body)>`. Raises `WebhookSignatureError` / `WebhookTimestampError` (both `WebhookVerificationError`). Pass the raw bytes. `serve(webhook_secret=, on_event=)` does this for you.

## Exceptions

`AssemblyAIAgentsError` ← `ConfigurationError`, `RealtimeError(close_code)`, `WebhookVerificationError`, `DeviceAudioError`, `APIError(status, code, message, param, request_id, errors, raw)` ← `BadRequestError` 400/405, `AuthenticationError` 401, `NotFoundError` 404, `ConflictError` 409, `ValidationError` 422, `ServerError` 5xx, `ResponseError` (2xx non-JSON). `ErrorCode` plain-string constants. `DeviceAudioNotInstalledError(ImportError)`.

## Testing

```python
from assemblyai_agents.testing import create_tool_context, get_tool
ctx = create_tool_context(secrets={"k": "v"}, aborted=False, session_id=None)
ctx.http.stub("GET", url, status_code=200, json=..., text=None, headers=None); ctx.http.calls; ctx.log.records; ctx.secret("k")
await get_tool(agent, "name").invoke(context=ctx, **arguments)
```
Pin payloads with `agent.hosted_at("https://test.invalid", secret="s").to_request()`.

## Backend contracts (what the platform sends you)

- **Tool call**: `POST/PUT/PATCH` → JSON body of arguments; `GET/DELETE` → query params (strings; `serve()` restores types). Return JSON; stringified for the model. Non-2xx/timeout → the model is told it failed; the client sees nothing. Hostnames DNS-checked at deploy.
- **Reply request** (`reply=`): `POST {public_url}/v1/chat/completions`, `Authorization: Bearer <secret>`, always `stream: true` + `include_usage` — SSE required; ~10 s; `messages[0]` = prompt + platform guidance; greeting as `assistant`; `tools` nested with a second `type`; after a tool: `tool` message then a `system` note; **unestablished values refused**; pre-connect captures as an `aai_pre_connect_context` result; DTMF params stripped; refused calls arrive as prose; no session id; text-injected turns never arrive.
- **Pre-connect**: phone only, before answer, ≤800 ms, body carries `sends` values (caller number not guaranteed), response `returns` paths + top-level `greeting`/`reject`, fails open.
- **Webhook**: signed `POST`, verify raw body, respond 2xx, idempotent.

## Deprecated (one release)

`byo` module → `replies`. `llm=` → `reply=`. `@tool(http=)` → bare / `url=`. `serve(reply=, tool_secret=, llm_key=, pre_connect=)` → `agent.serve(secret=)`. `assign_agent(agent=)` → no-op. Removed outright: `ToolRouter`, `AgentConnection(tools=)`, `conn.tool()`, `client_resident_tool_names()`.
