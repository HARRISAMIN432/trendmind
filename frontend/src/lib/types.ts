export interface ArticleListItem {
  id: number;
  title: string;
  url: string;
  published_at: string | null;
  source_name: string | null;
  category: string | null;
  sub_category: string | null;
  importance: string | null;
  summary_short: string | null;
  key_takeaway: string | null;
  companies: string[];
  is_duplicate: boolean;
  duplicate_of_id: number | null;
}

export interface SourceRead {
  id: number;
  name: string;
  homepage_url: string | null;
}

export interface ArticleDetail extends ArticleListItem {
  clean_content: string | null;
  why_it_matters: string | null;
  technical_highlights: string | null;
  embedding_id: string | null;
  source: SourceRead | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedArticles {
  total: number;
  limit: number;
  offset: number;
  items: ArticleListItem[];
}

export interface SearchResultItem {
  article: ArticleListItem;
  score: number;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResultItem[];
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatCitation {
  article: ArticleListItem;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  citations: ChatCitation[];
  context_article_count: number;
}

export interface TrendRead {
  id: number;
  title: string;
  description: string | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
  article_count: number;
}

export interface TrendDetail extends TrendRead {
  articles: ArticleListItem[];
}

export interface PaginatedTrends {
  total: number;
  limit: number;
  offset: number;
  items: TrendRead[];
}

export interface CompanyListItem {
  id: number;
  name: string;
  article_count: number;
}

export interface PaginatedCompanies {
  total: number;
  limit: number;
  offset: number;
  items: CompanyListItem[];
}

export interface CompanyProfile {
  id: number;
  name: string;
  article_count: number;
  first_mentioned_at: string | null;
  last_mentioned_at: string | null;
  category_breakdown: Record<string, number>;
  overview: string;
  timeline_highlights: string[];
  products: string[];
  funding_mentions: string[];
  articles: ArticleListItem[];
}

export interface GraphNodeItem {
  id: number;
  name: string;
  type: string;
}

export interface GraphEdgeItem {
  id: number;
  source_id: number;
  target_id: number;
  relation: string;
  article_id: number | null;
}

export interface GraphResponse {
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
}

export interface RecommendedArticle {
  article: ArticleListItem;
  score: number;
  matched_category: boolean;
}

export interface RecommendationResponse {
  recommendations: RecommendedArticle[];
  profile_categories: Record<string, number>;
  read_count_used: number;
}

export interface ArticlesQuery {
  limit?: number;
  offset?: number;
  category?: string;
  importance?: string;
  search?: string;
  sort_by?: "published_at" | "created_at";
}
