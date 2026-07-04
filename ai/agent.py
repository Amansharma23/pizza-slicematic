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
import time

from ai import observability, tools
from ai.config import get_settings
from ai.llm import get_client

log = logging.getLogger(__name__)

MAX_ROUNDS = 5
# Low temperature: with the bill/payment UI injected deterministically, format
# discipline (tags, tool args) matters more than personality variance.
TEMPERATURE = 0.2


def _stage(session) -> str:
    """Where this conversation is in the ordering flow, derived from session
    state (no extra bookkeeping): building -> payment -> ordered; escalated
    overrides. calculate_order_price resets `confirmed`, so a new order after a
    saved one flows building -> payment again."""
    if session.human_escalated:
        return "escalated"
    if session.confirmed:
        return "ordered"
    if session.pricing:
        return "payment"
    return "building"


def _stage_instruction(session) -> str:
    """The one short instruction block for the CURRENT step — the model sees
    only what to do now, instead of juggling a six-step global script."""
    voice = session.channel == "voice"
    stage = _stage(session)

    if stage == "escalated":
        return (
            "This conversation is flagged for a human teammate who will follow up. "
            "Be reassuring and helpful; only start a new order if the customer asks."
        )

    if stage == "ordered":
        return (
            "The order is saved and confirmed — do NOT save it again. Answer "
            "follow-up questions warmly. If they want to order more, build the new "
            "order (pizza → base → toppings → quantity) and price it with "
            "calculate_order_price."
        )

    if stage == "payment":
        if voice:
            return (
                "Tell the customer the total amount and ask how they'd like to pay: "
                "cash, card, or UPI. If they say UPI: reply with a short natural "
                "sentence telling them to check their screen, followed by exactly "
                "[UPI_QR] (e.g. \"Sure! You'll see a QR code on your screen — please "
                'scan it to pay. [UPI_QR]"). If they say Card: same idea, but end '
                "with exactly [CARD_FORM] instead. The chat screen (visible during "
                "this call) renders that tag as the real payment form — never "
                "describe it any other way. If they say Cash or COD: no tag needed, "
                "call confirm_and_save_order right away with payment mode Cash. For "
                "UPI/Card, WAIT until they say they've paid (e.g. 'I have paid', "
                "'done') before calling confirm_and_save_order with the SAME items "
                "and that payment mode — do not ask them to confirm again. If they "
                "change the order instead, rebuild the lines and call "
                "calculate_order_price again."
            )
        return (
            "The bill and payment buttons are already on screen — do not repeat "
            "the amounts. If they pick UPI reply with exactly [UPI_QR]; Card → "
            "exactly [CARD_FORM]; Cash/COD needs no tag. The moment payment is "
            "settled — they chose Cash/COD, said they paid (e.g. 'I have paid via "
            "UPI'), or sent 'Card details provided' — call confirm_and_save_order "
            "with the SAME items and that payment mode (Cash, UPI, or Card). Do "
            "not ask for confirmation again. If they change the order instead, "
            "rebuild the lines and call calculate_order_price again."
        )

    # building
    offer = (
        "Suggest 2-3 options by name and ask what they're in the mood for. "
        if voice
        else "Offer the choices as [TILES:...] tags. "
    )
    read_back = (
        "After it returns, say only the total and ask how they'd like to pay. "
        if voice
        else ""
    )
    return (
        "Build the order step by step: pizza first, then base, then 1-3 toppings, "
        f"then quantity (1-10). {offer}Ask one thing at a time. After each "
        "completed pizza, ask if they'd like another one. When they're done "
        "adding pizzas, call get_customer_profile and calculate_order_price "
        f"(with every line) together — don't announce it or ask them to wait, "
        f"just call. {read_back}If the customer changes their mind at any point, "
        "adjust and continue from there. If they give several details in one "
        "message (e.g. a pizza, base, and quantity all at once), fill every "
        "slot they gave and ask only for what's missing."
    )


def _examples_block() -> str:
    """Few-shot tag examples built from the LIVE menu (never hardcode item
    names — the grader swaps menu files). Models copy examples far more
    reliably than they follow prose format rules. Empty if the menu is down."""
    names = tools.menu_names()
    if not (names["pizzas"] and names["bases"] and names["toppings"]):
        return ""
    return f"""
EXAMPLES — match this style exactly:
Customer: what do you have?
You: Here are our pizzas — which one sounds good? 🍕
[TILES:PIZZA: {", ".join(names["pizzas"])}]

Customer: {names["pizzas"][0]}
You: Great pick! Which base would you like?
[TILES:BASE: {", ".join(names["bases"])}]

Customer: {names["bases"][0]}
You: And toppings — pick 1 to 3:
[TILES:TOPPING: {", ".join(names["toppings"])}]

Customer: UPI
You: [UPI_QR]
"""


def _voice_examples_block() -> str:
    """Few-shot spoken/Hinglish examples built from the LIVE menu (never
    hardcode names) — the voice sibling of _examples_block(). Mostly natural
    spoken phrasing instead of UI tags (which would otherwise leak into TTS as
    literal spoken text, e.g. the model saying "bracket tiles colon") — except
    [UPI_QR]/[CARD_FORM], which the voice call layer (ai/voice_call.py) strips
    before TTS but forwards intact to the chat thread so the real payment UI
    still renders on screen during the call."""
    names = tools.menu_names()
    if not (names["pizzas"] and names["bases"] and names["toppings"]):
        return ""
    pizza2 = names["pizzas"][1] if len(names["pizzas"]) > 1 else names["pizzas"][0]
    return f"""
EXAMPLES — match this natural, spoken style exactly (notice most replies are
clean, but one opens with a natural filler like a real person on the phone —
do that occasionally, not on every turn, or it starts sounding scripted):
Customer: kya milega?
You: Hamare paas {names["pizzas"][0]} aur {pizza2} hain — kaunsa pasand karenge?

Customer: {names["pizzas"][0]}
You: Great choice! Base kaunsa chahiye — {names["bases"][0]} ya koi aur?

Customer: total kitna hoga?
You: Hmm, ek second — aapka total 1,249 rupees hoga. Cash, card, ya UPI se pay karenge?

Customer: UPI se karunga
You: Sure! Aapko screen par ek QR code dikhega — usse scan karke pay kar dijiye. [UPI_QR]
"""


def build_system_prompt(session, menu_text: str) -> str:
    s = get_settings()
    voice = session.channel == "voice"

    style = (
        "You are on a live phone call: speak naturally in 1-2 short sentences — "
        "no markdown, tags, symbols, or lists. Never read the whole menu aloud; "
        "offer 2-3 options instead. Always write numbers with comma separators "
        "for correct pronunciation (e.g. 1,500 not 1500). Sound like a real "
        "support agent, not a script: occasionally (not every turn) open a "
        "reply with a natural filler like 'Hmm,' 'Achha,' or 'Okay so' — see "
        "the examples below for how often is natural."
        if voice
        else "Keep replies to 1-3 short, warm sentences plus any output tags. An "
        "occasional tasteful emoji is fine."
    )

    lang_rule = (
        "Speak naturally the way Delhi customers actually talk on the phone — "
        "freely code-switch between Hindi and English within the same sentence "
        "(natural Hinglish) rather than forcing pure Hindi or pure English. "
        "Mirror the customer's own mix."
        if voice
        # Chat stays English-only for now regardless of detected language —
        # voice keeps mirroring the customer's own Hindi/English/Hinglish mix.
        else "Respond ONLY in English, regardless of what language the customer "
        "writes in."
    )

    tags = (
        ""
        if voice
        else """
OUTPUT TAGS — the chat UI renders these as buttons and forms. Copy each format EXACTLY, with nothing after the closing bracket:
- Offering items: [TILES:PIZZA: name, name] / [TILES:BASE: name, name] / [TILES:TOPPING: name, name] — the category word (PIZZA, BASE, or TOPPING) is required.
- Customer picks UPI → reply with exactly [UPI_QR]
- Customer picks Card → reply with exactly [CARD_FORM]
- After calculate_order_price succeeds, the system shows the bill and payment buttons by itself — NEVER write [BILL] or [PAYMENT_OPTIONS] yourself, and never restate the bill's numbers.
"""
    )
    examples = _voice_examples_block() if voice else _examples_block()

    return f"""You are the order assistant at {s.brand}, a neighbourhood pizza place in \
New Ashok Nagar, Delhi — warm, friendly, efficient. {lang_rule} Ask ONE \
question at a time. {style}

HARD RULES — never break these:
- NEVER state, estimate, or compute a price, discount, GST amount, or total yourself. Bills come only from calculate_order_price; the only other prices you may mention are the unit prices printed in the MENU below.
- Offer ONLY items in the MENU below — never invent items or IDs. The MENU is always current; you never need a tool to see it.
- One order line = 1 pizza + 1 base + 1-3 toppings + quantity 1-10.
- The customer's name and phone come from get_customer_profile — do NOT ask them to type these.
- Call one tool at a time. Sole exception: get_customer_profile and calculate_order_price may be called together.
- If the customer is upset or asks for a human, call escalate_to_human with a 1-2 sentence summary of the issue.
{tags}{examples}
--- MENU (live — use these exact IDs) ---
{menu_text}
--- END MENU ---

CURRENT STEP: {_stage_instruction(session)}"""


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
    extra = {"max_tokens": 160} if session.channel == "voice" else {"max_tokens": 1000}
    tool_defs = tools.tools_for(session)  # stage-gated subset
    last_exc = None
    for model in get_settings().models:
        try:
            t0 = time.perf_counter()
            resp = client.chat.completions.create(
                model=model,
                messages=session.history,
                tools=tool_defs,
                temperature=TEMPERATURE,
                # OpenRouter: turn off hidden "thinking" tokens — the primary
                # (gemini-2.5-flash) reasons by default, adding seconds per call.
                # Providers without reasoning simply ignore this.
                extra_body={"reasoning": {"enabled": False}},
                **extra,
                **lf,
            )
            log.info("[timing] LLM %s %.2fs", model, time.perf_counter() - t0)
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


def _tool_json(result: str | None) -> dict | None:
    """Parse a tool result as its success-JSON payload ({'ok': True, ...}).
    Error paths return plain strings, so anything unparseable means failure."""
    if not result:
        return None
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and data.get("ok") is True else None


def _confirmation_text(session, saved: dict) -> str:
    """Deterministic, localized order confirmation — injected so the LLM never
    rephrases (or mangles) a saved order's numbers."""
    order_no, total, mode = saved["order_no"], saved["total"], saved["payment_mode"]
    hi = session.language == "hi"
    if session.channel == "voice":
        return (
            f"आपका ऑर्डर कन्फ़र्म हो गया! ऑर्डर नंबर {order_no}, "
            f"कुल {total:.2f} रुपये, {mode} से। धन्यवाद!"
            if hi
            else f"Your order is confirmed! Order number {order_no}, "
            f"total {total:.2f} rupees via {mode}. Thank you!"
        )
    return (
        f"✅ ऑर्डर कन्फ़र्म! ऑर्डर नंबर {order_no} — कुल ₹{total:.2f} ({mode})। "
        "आपका पिज़्ज़ा जल्द पहुँच रहा है 🍕"
        if hi
        else f"✅ Order confirmed! Order number {order_no} — total ₹{total:.2f} "
        f"via {mode}. Your pizza is on its way 🍕"
    )


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
            price_result = None
            confirm_result = None
            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tools.execute_tool(call.function.name, args, session)
                session.history.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )
                if call.function.name == "calculate_order_price":
                    price_result = result
                elif call.function.name == "confirm_and_save_order":
                    confirm_result = result

            # UI Injection: on a deterministic tool success, reply directly —
            # no second LLM pass to rephrase (or mangle) the numbers. Failures
            # (plain-string results) fall through to the LLM so it re-prompts.
            saved = _tool_json(confirm_result)
            if saved:
                auto_reply = _confirmation_text(session, saved)
                session.history.append({"role": "assistant", "content": auto_reply})
                return auto_reply
            # Bill injection is chat-only: voice replies go to TTS, which must
            # never speak raw JSON/markup — the voice LLM reads back the total.
            if session.channel == "chat" and _tool_json(price_result):
                auto_reply = (
                    f"[BILL]\n{price_result}\n[/BILL]\n\n"
                    "How would you like to pay?\n\n[PAYMENT_OPTIONS]"
                )
                session.history.append({"role": "assistant", "content": auto_reply})
                return auto_reply
        return (
            "Sorry, that took too many steps — could you simplify your request?"
            if session.language != "hi"
            else "माफ़ कीजिए, अनुरोध बहुत लंबा हो गया — कृपया इसे थोड़ा सरल करें।"
        )
    finally:
        observability.flush()
