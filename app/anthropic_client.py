import anthropic
from pathlib import Path

from app.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from app.system_prompt import SYSTEM_PROMPT

BETAS = ["code-execution-2025-08-25", "files-api-2025-04-14"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# In-memory session store: session_id -> {container_id, file_id, messages}
sessions: dict[str, dict] = {}


def upload_file(file_path: Path) -> str:
    """Upload a file to Anthropic Files API. Returns file_id."""
    result = client.beta.files.upload(file=file_path)
    return result.id


def create_session(session_id: str, file_id: str) -> None:
    """Initialize a session with a file_id."""
    sessions[session_id] = {
        "container_id": None,
        "file_id": file_id,
        "messages": [],
    }


def analyze_spreadsheet(session_id: str, user_message: str) -> str:
    """Send analysis request or follow-up question. Returns markdown response."""
    session = sessions.get(session_id)
    if not session:
        raise ValueError(f"No session found for {session_id}")

    file_id = session["file_id"]

    # Build user content blocks
    user_content = []

    # On first message, attach the file
    if not session["messages"]:
        user_content.append({"type": "container_upload", "file_id": file_id})

    user_content.append({"type": "text", "text": user_message})

    session["messages"].append({"role": "user", "content": user_content})

    # Build API call kwargs
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "betas": BETAS,
        "messages": session["messages"],
        "tools": [{"type": "code_execution_20250825", "name": "code_execution"}],
    }

    # Reuse container if we have one from a previous turn
    if session.get("container_id"):
        kwargs["container"] = session["container_id"]

    response = client.beta.messages.create(**kwargs)

    # Handle pause_turn: keep calling until we get a full response
    while response.stop_reason == "pause_turn":
        # Append the assistant's partial response and continue
        session["messages"].append({"role": "assistant", "content": response.content})
        session["messages"].append({"role": "user", "content": [{"type": "text", "text": "Please continue."}]})

        if hasattr(response, "container") and response.container:
            session["container_id"] = response.container.id
            kwargs["container"] = session["container_id"]

        kwargs["messages"] = session["messages"]
        response = client.beta.messages.create(**kwargs)

    # Extract container_id for reuse
    if hasattr(response, "container") and response.container:
        session["container_id"] = response.container.id

    # Parse response content blocks into markdown
    reply_parts = []
    for block in response.content:
        if hasattr(block, "type"):
            if block.type == "text":
                reply_parts.append(block.text)
            elif block.type == "server_tool_use":
                # Optionally show the code Claude executed
                if hasattr(block, "input"):
                    inp = block.input
                    if isinstance(inp, dict) and "command" in inp:
                        reply_parts.append(
                            f"\n<details><summary>Code executed</summary>\n\n```bash\n{inp['command']}\n```\n</details>\n"
                        )

    full_reply = "\n".join(reply_parts)

    # Store assistant turn for multi-turn conversation
    session["messages"].append({"role": "assistant", "content": response.content})

    return full_reply
