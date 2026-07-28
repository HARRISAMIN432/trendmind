"use client";

import { SearchBar } from "@/components/SearchBar";
import { ArticleCard } from "@/components/ArticleCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { SearchResultItem } from "@/lib/types";

interface SearchResultsViewProps {
  query: string;
  results: SearchResultItem[];
  error: string | null;
}

export function SearchResultsView({
  query,
  results,
  error,
}: SearchResultsViewProps) {
  const hasQuery = query.length > 0;

  return (
    <div className="px-6 py-6">
      <div className="mb-8 max-w-2xl">
        <SearchBar initialQuery={query} autoFocus />
      </div>

      {!hasQuery && (
        <EmptyState
          title="Semantic search"
          description="Enter a natural language query to find relevant AI news by meaning, powered by local embeddings and Chroma."
        />
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}

      {hasQuery && !error && results.length === 0 && (
        <EmptyState
          title="No results"
          description={`No articles matched "${query}". Try a different phrasing.`}
        />
      )}

      {results.length > 0 && (
        <div>
          <p className="mb-4 text-sm text-[var(--text-muted)]">
            {results.length} result{results.length === 1 ? "" : "s"} for &ldquo;
            {query}&rdquo;
          </p>
          <div className="space-y-4">
            {results.map(({ article, score }) => (
              <ArticleCard key={article.id} article={article} score={score} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
