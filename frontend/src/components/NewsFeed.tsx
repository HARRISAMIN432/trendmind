"use client";

import { useCallback, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArticleCard } from "@/components/ArticleCard";
import { CategoryFilter, ImportanceFilter } from "@/components/CategoryFilter";
import { Pagination } from "@/components/Pagination";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchRecommendations } from "@/lib/api";
import { ARTICLES_PER_PAGE } from "@/lib/constants";
import { getReadUrls } from "@/lib/read-history";
import type { ArticleListItem, PaginatedArticles } from "@/lib/types";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type FeedTab = "latest" | "for-you";

interface NewsFeedProps {
  initialData: PaginatedArticles;
  initialCategory: string | null;
  initialImportance: string | null;
  initialOffset: number;
}

export function NewsFeed({
  initialData,
  initialCategory,
  initialImportance,
  initialOffset,
}: NewsFeedProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [tab, setTab] = useState<FeedTab>("latest");
  const [recommendations, setRecommendations] = useState<ArticleListItem[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState<string | null>(null);
  const [recsLoaded, setRecsLoaded] = useState(false);

  const category = searchParams.get("category") ?? initialCategory;
  const importance = searchParams.get("importance") ?? initialImportance;
  const offset = Number(searchParams.get("offset") ?? initialOffset);

  const updateParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === "") params.delete(key);
        else params.set(key, value);
      }
      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
    },
    [router, searchParams],
  );

  const loadRecommendations = useCallback(async () => {
    const readUrls = getReadUrls();
    if (readUrls.length === 0) {
      setRecommendations([]);
      setRecsError("Read a few articles to get personalized recommendations.");
      setRecsLoaded(true);
      return;
    }

    setLoadingRecs(true);
    setRecsError(null);

    try {
      const res = await fetchRecommendations(readUrls, ARTICLES_PER_PAGE);
      setRecommendations(res.recommendations.map((r) => r.article));
      setRecsLoaded(true);
      if (res.recommendations.length === 0) {
        setRecsError("No recommendations found for your reading history.");
      }
    } catch {
      setRecsError("Could not load recommendations. Is the backend running?");
      setRecommendations([]);
      setRecsLoaded(true);
    } finally {
      setLoadingRecs(false);
    }
  }, []);

  const handleTabChange = (nextTab: FeedTab) => {
    setTab(nextTab);
    if (nextTab === "for-you" && !recsLoaded && !loadingRecs) {
      void loadRecommendations();
    }
  };

  const articles = tab === "for-you" ? recommendations : initialData.items;
  const showPagination = tab === "latest";

  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex gap-1 rounded-lg bg-[var(--bg-secondary)] p-1">
          {(
            [
              { id: "latest" as const, label: "Latest" },
              { id: "for-you" as const, label: "For You" },
            ] as const
          ).map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => handleTabChange(id)}
              aria-pressed={tab === id}
              className={cn(
                "rounded-md px-4 py-2 text-sm font-medium transition-all",
                tab === id
                  ? "bg-[var(--accent)] font-semibold text-white shadow-sm ring-2 ring-[var(--accent)]/30 ring-offset-1 ring-offset-[var(--bg-secondary)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "latest" && (
          <ImportanceFilter
            selected={importance}
            onChange={(value) =>
              updateParams({ importance: value, offset: "0" })
            }
          />
        )}
      </div>

      {tab === "latest" && (
        <div className="mb-6">
          <CategoryFilter
            selected={category}
            onChange={(value) => updateParams({ category: value, offset: "0" })}
          />
        </div>
      )}

      {(isPending || loadingRecs) && (
        <div className="mb-4 flex items-center gap-2 text-sm text-[var(--text-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading...
        </div>
      )}

      {tab === "for-you" &&
        recsError &&
        articles.length === 0 &&
        recsLoaded && (
          <EmptyState
            title="Nothing to recommend yet"
            description={recsError}
          />
        )}

      {tab === "latest" && articles.length === 0 && !isPending && (
        <EmptyState
          title="No articles found"
          description="Try adjusting your filters, or run the ingestion pipeline to populate articles."
        />
      )}

      {articles.length > 0 && (
        <div className="space-y-4">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}

      {showPagination && initialData.total > 0 && (
        <div className="mt-8">
          <Pagination
            total={initialData.total}
            limit={ARTICLES_PER_PAGE}
            offset={offset}
            onPageChange={(nextOffset) =>
              updateParams({ offset: String(nextOffset) })
            }
          />
        </div>
      )}
    </div>
  );
}
