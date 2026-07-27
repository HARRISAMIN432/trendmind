from pydantic import BaseModel, Field

CATEGORIES = [
    "Research",
    "Product Launch",
    "Funding",
    "Policy & Regulation",
    "Business & Industry",
    "Open Source",
    "Opinion & Analysis",
    "Other",
]

IMPORTANCE_LEVELS = ["High", "Medium", "Low"]


class ClassificationResult(BaseModel):
    category: str = Field(
        description=f"Best-fit single category from: {', '.join(CATEGORIES)}"
    )
    sub_category: str = Field(
        description="A short (1-3 word) more specific label within the category, "
        "e.g. 'LLM Benchmark', 'Seed Round', 'EU AI Act'."
    )
    companies: list[str] = Field(
        default_factory=list,
        description="Canonical names of companies/orgs meaningfully discussed in the "
        "article (not just mentioned in passing). Use official names, e.g. "
        "'OpenAI' not 'Open AI' or 'openai.com'.",
    )
    importance: str = Field(
        description=f"One of: {', '.join(IMPORTANCE_LEVELS)}. High = major news "
        "likely to affect the industry broadly; Medium = notable but narrower "
        "impact; Low = incremental or minor."
    )


CLASSIFICATION_SYSTEM_PROMPT = """You are a precise news classification engine for \
an AI industry news platform. You read one cleaned article at a time and return \
structured classification data. Be conservative with the "companies" list: only \
include an org if the article substantively discusses it, not every name that \
appears once. Never invent information not present in the article."""


def build_classification_prompt(title: str, clean_content: str) -> str:
    # Truncate to keep prompts cheap and within free-tier context/rate limits.
    content = clean_content[:6000]
    return (
        f"{CLASSIFICATION_SYSTEM_PROMPT}\n\n"
        f"Article title: {title}\n\n"
        f"Article content:\n{content}\n\n"
        "Classify this article now."
    )