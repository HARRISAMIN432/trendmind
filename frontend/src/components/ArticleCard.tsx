import Link from "next/link";
import type { ArticleListItem } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";
import { ImportanceBadge, Badge } from "./ui/Badge";
import { ExternalLink } from "lucide-react";

interface ArticleCardProps {
  article: ArticleListItem;
  score?: number;
}

export function ArticleCard({ article, score }: ArticleCardProps) {
  return (
    <article className="group animate-fade-in rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5 transition-colors hover:border-[var(--accent)]/30">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
          {article.source_name && (
            <span className="font-medium text-[var(--text-secondary)]">
              {article.source_name}
            </span>
          )}
          {article.source_name && <span>·</span>}
          <time
            dateTime={article.published_at ?? undefined}
            suppressHydrationWarning
          >
            {formatRelativeTime(article.published_at)}
          </time>
          {score !== undefined && (
            <>
              <span>·</span>
              <span>{Math.round(score * 100)}% match</span>
            </>
          )}
        </div>
        <ImportanceBadge importance={article.importance} />
      </div>

      <Link href={`/article/${article.id}`} className="block">
        <h2 className="text-base font-semibold leading-snug text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
          {article.title}
        </h2>
      </Link>

      {(article.summary_short || article.key_takeaway) && (
        <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-[var(--text-secondary)]">
          {article.summary_short ?? article.key_takeaway}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {article.category && <Badge variant="accent">{article.category}</Badge>}
        {article.sub_category && (
          <Badge variant="outline">{article.sub_category}</Badge>
        )}
        {article.companies.slice(0, 3).map((company) => (
          <Badge key={company} variant="outline">
            {company}
          </Badge>
        ))}
        {article.companies.length > 3 && (
          <Badge variant="muted">+{article.companies.length - 3}</Badge>
        )}
      </div>

      <div className="mt-4 flex items-center gap-4 border-t border-[var(--border-subtle)] pt-3">
        <Link
          href={`/article/${article.id}`}
          className="text-xs font-medium text-[var(--accent)] transition-colors hover:text-[var(--accent-hover)]"
        >
          Read analysis
        </Link>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-[var(--text-muted)] transition-colors hover:text-[var(--text-secondary)]"
        >
          Source
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </article>
  );
}
