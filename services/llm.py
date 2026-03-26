"""
LLM Service
- Primary:  GPT-4o mini  (default, cost-efficient)
- Premium:  Claude Haiku (optional, per site plan)
"""
from openai import AsyncOpenAI
import anthropic
from core.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) \
    if settings.ANTHROPIC_API_KEY else None


def build_system_prompt(site: dict, disclaimer: str) -> str:
    site_name = site.get("site_name", "this website")
    prompt = f"""You are a helpful AI assistant for {site_name}.
Your role is to answer questions based ONLY on the provided website content.

Rules:
- Answer only from the context provided below
- If the answer is not in the context, say "I don't have that information on this website. Please contact us directly."
- Be concise, friendly, and helpful
- Never make up information
- If asked about pricing or sensitive data not in context, direct the user to contact the business
"""
    if disclaimer:
        prompt += f"\n\nIMPORTANT DISCLAIMER TO PREPEND TO EVERY RESPONSE:\n{disclaimer}\n"

    return prompt


async def generate_answer_openai(
    user_message: str,
    context_chunks: list[str],
    site: dict,
    disclaimer: str,
    conversation_history: list = None,
) -> tuple[str, int]:
    """
    Generate answer using GPT-4o mini.
    Returns (answer_text, tokens_used)
    """
    context = "\n\n---\n\n".join(context_chunks)
    system_prompt = build_system_prompt(site, disclaimer)

    messages = []
    # Include recent conversation history for context
    if conversation_history:
        messages.extend(conversation_history[-6:])  # last 3 turns

    messages.append({
        "role": "user",
        "content": f"Context from website:\n\n{context}\n\nUser question: {user_message}"
    })

    response = await openai_client.chat.completions.create(
        model=settings.PRIMARY_LLM,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.3,
        max_tokens=600,
    )

    answer = response.choices[0].message.content
    tokens = response.usage.total_tokens
    return answer, tokens


async def generate_answer_claude(
    user_message: str,
    context_chunks: list[str],
    site: dict,
    disclaimer: str,
    conversation_history: list = None,
) -> tuple[str, int]:
    """
    Generate answer using Claude Haiku (premium tier).
    Returns (answer_text, tokens_used)
    """
    if not anthropic_client:
        raise ValueError("Anthropic API key not configured")

    context = "\n\n---\n\n".join(context_chunks)
    system_prompt = build_system_prompt(site, disclaimer)

    messages = []
    if conversation_history:
        messages.extend(conversation_history[-6:])

    messages.append({
        "role": "user",
        "content": f"Context from website:\n\n{context}\n\nUser question: {user_message}"
    })

    response = await anthropic_client.messages.create(
        model=settings.PREMIUM_LLM,
        system=system_prompt,
        messages=messages,
        temperature=0.3,
        max_tokens=600,
    )

    answer = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return answer, tokens


async def generate_answer(
    user_message: str,
    context_chunks: list[str],
    site: dict,
    disclaimer: str,
    conversation_history: list = None,
) -> tuple[str, int]:
    """
    Route to correct LLM based on site's plan/model setting.
    """
    model = site.get("llm_model", "gpt-4o-mini")

    if model == "claude-haiku" and anthropic_client:
        return await generate_answer_claude(
            user_message, context_chunks, site, disclaimer, conversation_history
        )
    else:
        return await generate_answer_openai(
            user_message, context_chunks, site, disclaimer, conversation_history
        )
