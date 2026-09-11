"""What the deployed agent looks like on the wire."""

import agent as agent_module
from assemblyai_agents.models.rest import HttpMethod


def test_every_tool_is_served_by_this_process():
    # Bare tools are hosted here; the deploy binds them to PUBLIC_BASE_URL.
    assert set(agent_module.agent.hosted_tool_names()) == {t.name for t in agent_module.TOOLS}
    for tool in agent_module.agent.to_request().tools:
        assert tool.http is not None
        assert tool.http.url.startswith("https://starter.test.local/tools/")
        assert tool.http.http_method == HttpMethod.POST
        assert tool.http.headers[0].name == "Authorization"


def test_the_tools_take_what_the_caller_said_rather_than_a_derived_value():
    # The platform refuses an argument whose value the conversation never
    # established, so anything the caller speaks is passed through verbatim and
    # read at the backend.
    tools = {tool.name: tool for tool in agent_module.agent.to_request().tools}

    assert "caller_said" in tools["verify_caller"].parameters["properties"]
    assert "reference_said" in tools["find_patient"].parameters["properties"]


def test_the_lookup_hands_back_nothing_identifying():
    # The caller states their own name; the tool checks it. A lookup that
    # returned the name would let the agent greet an unverified caller by it.
    import asyncio

    result = asyncio.run(agent_module.find_patient.invoke(reference_said="four four seven one"))

    assert result["found"] is True
    joined = str(result).lower()
    assert "delgado" not in joined and "maria" not in joined


def test_the_pre_connect_lookup_may_rewrite_the_greeting():
    entry = agent_module.agent.to_request().pre_connect_requests[0]

    assert entry.http.url == "https://starter.test.local/pre-connect/lookup"
    assert entry.allow_overrides == ["greeting"]
    assert entry.timeout_ms <= 800
    assert {captured.name for captured in entry.returns} == {"reference", "first_name"}


def test_replies_come_from_our_own_endpoint():
    llm = agent_module.agent.to_request().llm[0]
    assert llm.base_url == "https://starter.test.local/v1"
    assert agent_module.agent.hosts_replies


def test_the_greeting_names_the_practice_and_the_recording():
    greeting = agent_module.agent.greeting
    assert "Fairview Dental" in greeting
    assert "recorded line" in greeting


def test_expose_is_the_same_file_as_the_examples_copy():
    """The starter ships its own `expose.py` so a copied project runs.

    Two copies drift, so this pins them together. If the examples copy changes,
    copy it over; when agent code can be deployed directly, both are deleted.
    """
    from pathlib import Path

    here = Path(__file__).resolve().parent.parent
    upstream = here.parent / "expose.py"
    if not upstream.exists():
        return  # this project has been copied out of the SDK repo; nothing to pin
    assert (here / "expose.py").read_text() == upstream.read_text()
