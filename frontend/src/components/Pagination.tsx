"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
}

export function Pagination({
  total,
  limit,
  offset,
  onPageChange,
}: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);

  return (
    <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
      <p className="text-sm text-[var(--text-muted)]">
        {total === 0
          ? "No articles"
          : `Showing ${start}–${end} of ${total} articles`}
      </p>

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(offset - limit)}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm transition-colors",
            currentPage <= 1
              ? "cursor-not-allowed opacity-40"
              : "hover:border-[var(--accent)] hover:text-[var(--accent)]",
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </button>
        <span className="px-2 text-sm text-[var(--text-secondary)]">
          Page {currentPage} of {totalPages}
        </span>
        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(offset + limit)}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm transition-colors",
            currentPage >= totalPages
              ? "cursor-not-allowed opacity-40"
              : "hover:border-[var(--accent)] hover:text-[var(--accent)]",
          )}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
