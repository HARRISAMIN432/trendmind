import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { ArticleCard } from "@/components/ArticleCard";
import { fetchTrend } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

interface TrendDetailPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: TrendDetailPageProps) {
  const { id } = await params;
  try {
    const trend = await fetchTrend(Number(id));
    return { title: trend.title };
  } catch {
    return { title: "Trend" };
  }
}

export default async function TrendDetailPage({ params }: TrendDetailPageProps) {
  const { id } = await params;
  const trendId = Number(id);
  if (Number.isNaN(trendId)) notFound();

  let trend;
  try {
    trend = await fetchTrend(trendId);
  } catch {
    notFound();
  }

  return (
    <AppShell>
      <div className="border-b border-[var(--border)] px-6 py-4">
        <Link
          href="/trends"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--accent)]"
        >
          <ArrowLeft className="h-4 w-4" />
          All trends
        </Link>
      </div>

      <Header
        title={trend.title}
        subtitle={
          trend.description ??
          `Cluster of ${trend.article_count} related articles.`
        }
      />

      <div className="px-6 py-6">
        <div className="mb-6 flex flex-wrap gap-4 text-sm text-[var(--text-muted)]">
          <span>
            {trend.article_count}{" "}
            {trend.article_count === 1 ? "article" : "articles"}
          </span>
          {trend.period_start && trend.period_end && (
            <span>
              Period: {formatDate(trend.period_start)} –{" "}
              {formatDate(trend.period_end)}
            </span>
          )}
        </div>

        <div className="space-y-4">
          {trend.articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      </div>
    </AppShell>
  );
}
