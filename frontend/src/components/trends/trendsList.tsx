"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/Pagination";
import { fetchTrends } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { PaginatedTrends } from "@/lib/types";

const PAGE_SIZE = 20;

export function TrendsList({ initialData }: { initialData: PaginatedTrends }) {
  const [data, setData] = useState(initialData);
  const [offset, setOffset] = useState(initialData.offset);
  const [isPending, startTransition] = useTransition();

  function handlePageChange(nextOffset: number) {
    setOffset(nextOffset);
    startTransition(async () => {
      try {
        const next = await fetchTrends(PAGE_SIZE, nextOffset);
        setData(next);
      } catch {
        // keep previous page's data on fetch failure
      }
    });
  }

  if (data.items.length === 0) {
    return <EmptyState title="No trends yet" description="" />;
  }

  return (
    <div className={isPending ? "opacity-60 transition-opacity" : undefined}>
      <p className="mb-3 text-sm text-[var(--text-muted)]">
        {data.total} trend{data.total === 1 ? "" : "s"} tracked
      </p>

      <div className="space-y-3">
        {data.items.map((trend) => (
          <Link
            key={trend.id}
            href={`/trends/${trend.id}`}
            className="group flex items-start justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5 transition-colors hover:border-[var(--accent)]/30"
          >
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-semibold text-[var(--text-primary)] group-hover:text-[var(--accent)]">
                {trend.title}
              </h2>
              {trend.description && (
                <p className="mt-2 line-clamp-2 text-sm text-[var(--text-secondary)]">
                  {trend.description}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--text-muted)]">
                <span>
                  {trend.article_count}{" "}
                  {trend.article_count === 1 ? "article" : "articles"}
                </span>
                {trend.period_start && trend.period_end && (
                  <span>
                    {formatDate(trend.period_start)} –{" "}
                    {formatDate(trend.period_end)}
                  </span>
                )}
              </div>
            </div>
            <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-[var(--text-muted)] group-hover:text-[var(--accent)]" />
          </Link>
        ))}
      </div>

      <div className="mt-6">
        <Pagination
          total={data.total}
          limit={PAGE_SIZE}
          offset={offset}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
}
