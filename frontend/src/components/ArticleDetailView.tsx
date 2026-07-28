"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ChatWidget } from "@/components/ChatWidget";
import { Badge, ImportanceBadge } from "@/components/ui/Badge";
import { addReadUrl } from "@/lib/read-history";
import type { ArticleDetail } from "@/lib/types";
import {
  encodeCompanyName,
  formatDate,
  formatRelativeTime,
} from "@/lib/utils";
import { ArrowLeft, ExternalLink } from "lucide-react";

interface ArticleDetailViewProps {
  article: ArticleDetail;
}

export function ArticleDetailView({ article }: ArticleDetailViewProps) {
  useEffect(() => {
    addReadUrl(article.url);
  }, [article.url]);

  return (
    <AppShell>
      <div className="border-b border-[var(--border)] px-6 py-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--accent)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to feed
        </Link>
      </div>

      <div className="grid gap-8 px-6 py-6 xl:grid-cols-[1fr_380px]">
        <article>
          <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-[var(--text-muted)]">
            {article.source_name && (
              <span className="font-medium text-[var(--text-secondary)]">
                {article.source?.name ?? article.source_name}
              </span>
            )}
            <span>·</span>
            <time dateTime={article.published_at ?? undefined}>
              {formatDate(article.published_at)} (
              {formatRelativeTime(article.published_at)})
            </time>
            <ImportanceBadge importance={article.importance} />
          </div>

          <h1 className="text-2xl font-semibold leading-tight text-[var(--text-primary)]">
            {article.title}
          </h1>

          <div className="mt-4 flex flex-wrap gap-2">
            {article.category && (
              <Badge variant="accent">{article.category}</Badge>
            )}
            {article.sub_category && (
              <Badge variant="outline">{article.sub_category}</Badge>
            )}
            {article.companies.map((company) => (
              <Link
                key={company}
                href={`/company/${encodeCompanyName(company)}`}
              >
                <Badge variant="outline">{company}</Badge>
              </Link>
            ))}
          </div>

          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex items-center gap-1 text-sm text-[var(--accent)] transition-colors hover:text-[var(--accent-hover)]"
          >
            Read original article
            <ExternalLink className="h-4 w-4" />
          </a>

          {article.summary_short && (
            <section className="mt-8">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                Summary
              </h2>
              <p className="text-base leading-relaxed text-[var(--text-secondary)]">
                {article.summary_short}
              </p>
            </section>
          )}

          {article.key_takeaway && (
            <section className="mt-6 rounded-xl border border-[var(--accent)]/20 bg-[var(--accent-muted)] p-4">
              <h2 className="mb-2 text-sm font-semibold text-[var(--accent)]">
                Key Takeaway
              </h2>
              <p className="text-sm leading-relaxed text-[var(--text-primary)]">
                {article.key_takeaway}
              </p>
            </section>
          )}

          {article.why_it_matters && (
            <section className="mt-6">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                Why It Matters
              </h2>
              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                {article.why_it_matters}
              </p>
            </section>
          )}

          {article.technical_highlights && (
            <section className="mt-6">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                Technical Highlights
              </h2>
              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                {article.technical_highlights}
              </p>
            </section>
          )}
        </article>

        <aside className="xl:sticky xl:top-0 xl:self-start">
          <ChatWidget category={article.category} compact />
        </aside>
      </div>
    </AppShell>
  );
}
