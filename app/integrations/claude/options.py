from claude_agent_sdk import ClaudeAgentOptions

from app.core.config import Settings

SPOKEN_REPLY_RULES = (
    "You are JARVIS, the owner's personal assistant. Your replies are read aloud by a text-to-speech engine: "
    "answer in short plain sentences, without markdown, tables, lists or code blocks unless the owner asks for "
    "them. Reply in the language the owner spoke."
)


def build_options(settings: Settings, session_id: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        cwd=settings.JARVIS_VAULT_DIR,
        setting_sources=["project"],
        skills=list(settings.BRAIN_SKILLS),
        permission_mode="dontAsk",
        allowed_tools=list(settings.BRAIN_ALLOWED_TOOLS),
        system_prompt={"type": "preset", "preset": "claude_code", "append": SPOKEN_REPLY_RULES},
        model=settings.BRAIN_MODEL,
        effort=settings.BRAIN_EFFORT,
        resume=session_id,
        include_partial_messages=True,
    )
