import type {
  ArticleDetail,
  ArticlesQuery,
  ChatResponse,
  ChatTurn,
  CompanyProfile,
  GraphResponse,
  PaginatedArticles,
  PaginatedCompanies,
  PaginatedTrends,
  RecommendationResponse,
  SearchResponse,
  TrendDetail,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchArticles(
  query: ArticlesQuery = {},
): Promise<PaginatedArticles> {
  return request<PaginatedArticles>(
    `/articles${toQuery({
      limit: query.limit,
      offset: query.offset,
      category: query.category,
      importance: query.importance,
      search: query.search,
      sort_by: query.sort_by,
    })}`,
  );
}

export async function fetchArticle(id: number): Promise<ArticleDetail> {
  return request<ArticleDetail>(`/articles/${id}`);
}

export async function searchArticles(
  q: string,
  limit = 10,
  category?: string,
): Promise<SearchResponse> {
  return request<SearchResponse>(
    `/search${toQuery({ q, limit, category })}`,
  );
}

export async function sendChatMessage(
  question: string,
  history: ChatTurn[] = [],
  category?: string,
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      question,
      history,
      n_context_articles: 5,
      category,
    }),
  });
}

export async function fetchTrends(
  limit = 20,
  offset = 0,
): Promise<PaginatedTrends> {
  return request<PaginatedTrends>(
    `/trends${toQuery({ limit, offset })}`,
  );
}

export async function fetchTrend(id: number): Promise<TrendDetail> {
  return request<TrendDetail>(`/trends/${id}`);
}

export async function fetchCompanies(
  limit = 50,
  offset = 0,
): Promise<PaginatedCompanies> {
  return request<PaginatedCompanies>(
    `/companies${toQuery({ limit, offset })}`,
  );
}

export async function fetchCompanyProfile(
  name: string,
): Promise<CompanyProfile> {
  return request<CompanyProfile>(
    `/companies/${encodeURIComponent(name)}`,
  );
}

export async function fetchGraph(): Promise<GraphResponse> {
  return request<GraphResponse>("/graph");
}

export async function fetchRecommendations(
  readUrls: string[],
  limit = 10,
): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/recommendations", {
    method: "POST",
    body: JSON.stringify({ read_urls: readUrls, limit }),
  });
}

export { ApiError };
