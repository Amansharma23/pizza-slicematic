"""The agent loop: OpenRouter tool-calling with an app-level fallback chain.

One turn = build the system prompt (persona + live menu + detected language),
then loop: call the model with the tool definitions; if it returns tool calls,
execute them via ai/tools.py and feed the results back; stop at a plain-text
reply or after MAX_ROUNDS. Each model call falls back primary -> fallback1 ->
fallback2 so a single provider outage doesn't break the turn.
"""

from __future__ import annotations

import json
import logging

from ai import observability, tools
from ai.config import get_settings
from ai.llm import get_client

log = logging.getLogger(__name__)

MAX_ROUNDS = 5
TEMPERATURE = 0.5


def build_system_prompt(session, menu_text: str) -> str:
    s = get_settings()
    lang = "Hindi" if session.language == "hi" else "English"
    voice_note = (
        "\n\nVOICE CALL — you are on a live phone call, so:\n"
        "- Reply in 1-2 short, natural spoken sentences. No markdown, bullet lists, or symbols.\n"
        "- NEVER read a long list aloud. If asked about the menu, do NOT enumerate everything —"
        " mention 2-3 options and ask what they're in the mood for, or which category"
        " (base, pizza, or topping) they'd like to hear.\n"
        "- Read the bill back briefly (e.g. 'that comes to 677 rupees') — don't spell out every"
        " line item.\n"
        "- Ask one question at a time and keep the conversation moving."
        if session.channel == "voice"
        else ""
    )
    return f"""You are a warm, friendly counter staffer taking orders at {s.brand}, a
neighbourhood pizza place. Chat naturally — like a real person, not a form.
Respond ONLY in {lang}.

Goal: take the customer's pizza order, read back the itemised bill, get their
confirmation, then save it.

Always use the tools — never do these yourself:
- Never state or compute prices, discounts, GST, or totals. Only calculate_order_price does.
- Only offer items returned by get_menu. Never invent items or IDs.
- As the customer gives details, call validate_customer to check name/phone/payment.
- Call confirm_and_save_order ONLY after the customer confirms the bill AND you have a
  valid name, 10-digit phone (starting 6-9), and payment mode (Cash/Card/UPI).
- The moment the customer affirms the bill ("yes", "confirm", "place it"), call
  confirm_and_save_order right away — do NOT repeat the bill or ask again.
- If the customer asks for a human or is upset, call escalate_to_human, passing a brief
  1-2 sentence summary of the conversation and the issue as the reason.

Collect: name, phone, one or more lines of (base + pizza + topping + quantity 1-10), payment.

Current menu — use these exact IDs:
{menu_text}

Keep replies short, warm, and conversational. Use the customer's first name once
you know it, and an occasional tasteful emoji is fine.{voice_note}"""


def _assistant_to_dict(msg) -> dict:
    """Convert an OpenAI assistant message to a history dict (preserving tool calls)."""
    out: dict = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.function.name,
                    "arguments": c.function.arguments,
                },
            }
            for c in msg.tool_calls
        ]
    return out


def _complete(session):
    """One model call with app-level fallback across configured models."""
    client = get_client()
    lf = observability.trace_kwargs(
        session.id, f"{session.channel}-turn", language=session.language
    )
    # Cap voice replies to keep them short and fast to generate/speak.
    extra = {"max_tokens": 160} if session.channel == "voice" else {}
    last_exc = None
    for model in get_settings().models:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=session.history,
                tools=tools.TOOL_DEFINITIONS,
                temperature=TEMPERATURE,
                **extra,
                **lf,
            )
            return resp, model
        except Exception as exc:
            last_exc = exc
            log.warning("Model %s failed, trying next: %s", model, exc)
    raise last_exc if last_exc else RuntimeError("no models configured")


def _apology(language: str) -> str:
    if language == "hi":
        return "माफ़ कीजिए, अभी कुछ तकनीकी समस्या है। कृपया थोड़ी देर बाद दोबारा कोशिश करें।"
    return "Sorry, I'm having trouble right now. Please try again in a moment."


def _set_system_prompt(session) -> None:
    """Refresh history[0] with a current system prompt (menu/language may change)."""
    menu_text = tools.execute_tool("get_menu", {}, session)
    prompt = build_system_prompt(session, menu_text)
    if session.history and session.history[0].get("role") == "system":
        session.history[0]["content"] = prompt
    else:
        session.history.insert(0, {"role": "system", "content": prompt})


def run_turn(session, user_message: str) -> str:
    """Process one user message and return the assistant's reply text."""
    _set_system_prompt(session)
    session.add("user", user_message)
    try:
        for _ in range(MAX_ROUNDS):
            try:
                resp, model = _complete(session)
            except Exception as exc:
                log.warning("All models failed: %s", exc)
                return _apology(session.language)
            msg = resp.choices[0].message
            session.history.append(_assistant_to_dict(msg))
            if not msg.tool_calls:
                return msg.content or ""
            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tools.execute_tool(call.function.name, args, session)
                session.history.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )
        return (
            "Sorry, that took too many steps — could you simplify your request?"
            if session.language != "hi"
            else "माफ़ कीजिए, अनुरोध बहुत लंबा हो गया — कृपया इसे थोड़ा सरल करें।"
        )
    finally:
        observability.flush()
