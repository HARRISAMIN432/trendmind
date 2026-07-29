"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/Pagination";
import { fetchCompanies } from "@/lib/api";
import { encodeCompanyName } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { PaginatedCompanies } from "@/lib/types";

const PAGE_SIZE = 20;

export function CompaniesList({
  initialData,
}: {
  initialData: PaginatedCompanies;
}) {
  const [data, setData] = useState(initialData);
  const [offset, setOffset] = useState(initialData.offset);
  const [isPending, startTransition] = useTransition();

  function handlePageChange(nextOffset: number) {
    setOffset(nextOffset);
    startTransition(async () => {
      try {
        const next = await fetchCompanies(PAGE_SIZE, nextOffset);
        setData(next);
      } catch {
        // keep previous page's data on fetch failure
      }
    });
  }

  if (data.items.length === 0) {
    return (
      <EmptyState
        title="No companies tracked"
        description="Companies are extracted during article classification. Run the ingestion pipeline to populate this list."
      />
    );
  }

  return (
    <div className={isPending ? "opacity-60 transition-opacity" : undefined}>
      <p className="mb-4 text-sm text-[var(--text-muted)]">
        {data.total} {data.total === 1 ? "company" : "companies"} tracked
      </p>

      <div className="space-y-2">
        {data.items.map((company) => (
          <Link
            key={company.id}
            href={`/company/${encodeCompanyName(company.name)}`}
            className="group flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-5 py-4 transition-colors hover:border-[var(--accent)]/30"
          >
            <div>
              <p className="font-medium text-[var(--text-primary)] group-hover:text-[var(--accent)]">
                {company.name}
              </p>
              <p className="mt-0.5 text-sm text-[var(--text-muted)]">
                {company.article_count}{" "}
                {company.article_count === 1 ? "article" : "articles"}
              </p>
            </div>
            <ChevronRight className="h-5 w-5 text-[var(--text-muted)] group-hover:text-[var(--accent)]" />
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
