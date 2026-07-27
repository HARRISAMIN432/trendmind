from pydantic import BaseModel, Field

class SummarizationResult(BaseModel):
    summary_short: str = Field(
        description="A tight 3-sentence-max summary of the article, plain prose, "
        "no bullet points, no preamble like 'This article discusses...'."
    )
    key_takeaway: str = Field(
        description="The single most important fact or outcome from the article, "
        "in one sentence."
    )
    why_it_matters: str = Field(
        description="1-2 sentences on the broader significance for the AI industry "
        "— why a reader should care, not just what happened."
    )
    technical_highlights: str = Field(
        default="",
        description="Any concrete technical details worth surfacing (benchmark "
        "numbers, model sizes, architecture notes, dataset details). Empty string "
        "if the article has no technical content (e.g. pure funding/policy news).",
    )


SUMMARIZATION_SYSTEM_PROMPT = """You are a precise summarization engine for an AI \
industry news platform read by engineers and researchers. Write for someone who \
will not read the source article — be concrete and specific, never vague filler \
like "this is significant" without saying why. Do not invent facts, numbers, or \
quotes not present in the article. If the article provides category context, use \
it to calibrate tone (e.g. a Research article should lean on technical_highlights; \
a Funding article usually has none)."""


def build_summarization_prompt(
    title: str,
    clean_content: str,
    category: str | None = None,
    sub_category: str | None = None,
) -> str:
    content = clean_content[:8000]
    context_line = ""
    if category:
        context_line = f"Category: {category}" + (
            f" / {sub_category}" if sub_category else ""
        )
    return (
        f"{SUMMARIZATION_SYSTEM_PROMPT}\n\n"
        f"Article title: {title}\n"
        f"{context_line}\n\n"
        f"Article content:\n{content}\n\n"
        "Summarize this article now."
    )