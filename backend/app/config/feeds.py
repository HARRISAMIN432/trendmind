from dataclasses import dataclass

@dataclass(frozen=True)
class FeedConfig:
    name: str
    rss_url: str
    homepage_url: str | None = None

AI_NEWS_FEEDS: list[FeedConfig] = [
    FeedConfig(
        name="TechCrunch AI",
        rss_url="https://techcrunch.com/category/artificial-intelligence/feed/",
        homepage_url="https://techcrunch.com/category/artificial-intelligence/",
    ),
    FeedConfig(
        name="VentureBeat AI",
        rss_url="https://venturebeat.com/category/ai/feed/",
        homepage_url="https://venturebeat.com/category/ai/",
    ),
    FeedConfig(
        name="MIT Technology Review - AI",
        rss_url="https://www.technologyreview.com/topic/artificial-intelligence/feed",
        homepage_url="https://www.technologyreview.com/topic/artificial-intelligence/",
    ),
    FeedConfig(
        name="ArXiv cs.AI",
        rss_url="http://export.arxiv.org/rss/cs.AI",
        homepage_url="https://arxiv.org/list/cs.AI/recent",
    ),
    FeedConfig(
        name="The Verge AI",
        rss_url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        homepage_url="https://www.theverge.com/ai-artificial-intelligence",
    ),
    FeedConfig(
        name="Google News - AI",
        rss_url="https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
        homepage_url="https://news.google.com/",
    ),
]