import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { ArticleCard } from "@/components/ArticleCard";
import { Badge } from "@/components/ui/Badge";
import { fetchCompanyProfile } from "@/lib/api";
import { decodeCompanyName, formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

interface CompanyPageProps {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: CompanyPageProps) {
  const { name } = await params;
  const decoded = decodeCompanyName(name);
  return { title: decoded };
}

export default async function CompanyPage({ params }: CompanyPageProps) {
  const { name } = await params;
  const companyName = decodeCompanyName(name);

  let profile;
  try {
    profile = await fetchCompanyProfile(companyName);
  } catch {
    notFound();
  }

  return (
    <AppShell>
      <div className="border-b border-[var(--border)] px-6 py-4">
        <Link
          href="/companies"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--accent)]"
        >
          <ArrowLeft className="h-4 w-4" />
          All companies
        </Link>
      </div>

      <Header
        title={profile.name}
        subtitle={`Intelligence profile from ${profile.article_count} tracked ${profile.article_count === 1 ? "article" : "articles"}.`}
      />

      <div className="space-y-8 px-6 py-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Articles"
            value={String(profile.article_count)}
          />
          <StatCard
            label="First mentioned"
            value={formatDate(profile.first_mentioned_at)}
          />
          <StatCard
            label="Last mentioned"
            value={formatDate(profile.last_mentioned_at)}
          />
        </div>

        <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Overview
          </h2>
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {profile.overview}
          </p>
        </section>

        {Object.keys(profile.category_breakdown).length > 0 && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Category Breakdown
            </h2>
            <div className="flex flex-wrap gap-2">
              {Object.entries(profile.category_breakdown)
                .sort(([, a], [, b]) => b - a)
                .map(([category, count]) => (
                  <Badge key={category} variant="outline">
                    {category}: {count}
                  </Badge>
                ))}
            </div>
          </section>
        )}

        {profile.timeline_highlights.length > 0 && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Timeline Highlights
            </h2>
            <ul className="space-y-2">
              {profile.timeline_highlights.map((item, i) => (
                <li
                  key={i}
                  className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-sm text-[var(--text-secondary)]"
                >
                  {item}
                </li>
              ))}
            </ul>
          </section>
        )}

        {profile.products.length > 0 && (
          <ListSection title="Products" items={profile.products} />
        )}

        {profile.funding_mentions.length > 0 && (
          <ListSection title="Funding Mentions" items={profile.funding_mentions} />
        )}

        <section>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Related Articles
          </h2>
          {profile.articles.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">
              No articles found for this company.
            </p>
          ) : (
            <div className="space-y-4">
              {profile.articles.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3">
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
        {value}
      </p>
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
        {title}
      </h2>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li
            key={i}
            className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-sm text-[var(--text-secondary)]"
          >
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
