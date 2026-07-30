import Link from "next/link";
import { fetchCompanies, fetchTrends } from "@/lib/api";
import { encodeCompanyName } from "@/lib/utils";
import { Building2, TrendingUp } from "lucide-react";

export async function RightPanel() {
  let trends: Awaited<ReturnType<typeof fetchTrends>>["items"] = [];
  let companies: Awaited<ReturnType<typeof fetchCompanies>>["items"] = [];

  try {
    const [trendsData, companiesData] = await Promise.all([
      fetchTrends(5, 0),
      fetchCompanies(5, 0),
    ]);
    trends = trendsData.items;
    companies = companiesData.items;
  } catch {
    /* backend may be offline during build */
  }

  return (
    <div className="flex h-full flex-col gap-6 p-5">
      <section>
        <div className="mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Trending Topics
          </h2>
        </div>
        {trends.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No trends yet.</p>
        ) : (
          <ul className="space-y-2">
            {trends.map((trend, index) => (
              <li key={trend.id}>
                <Link
                  href={`/trends/${trend.id}`}
                  className="group flex items-start gap-3 rounded-lg p-2 transition-colors hover:bg-[var(--bg-tertiary)]"
                >
                  <span className="mt-0.5 w-4 text-xs font-medium text-[var(--text-muted)]">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-[var(--text-primary)] group-hover:text-[var(--accent)]">
                      {trend.title}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {trend.article_count}{" "}
                      {trend.article_count === 1 ? "article" : "articles"}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Building2 className="h-4 w-4 text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Top Companies
          </h2>
        </div>
        {companies.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">
            No companies tracked yet.
          </p>
        ) : (
          <ul className="space-y-1">
            {companies.map((company) => (
              <li key={company.id}>
                <Link
                  href={`/company/${encodeCompanyName(company.name)}`}
                  className="flex items-center justify-between rounded-lg px-2 py-2 text-sm transition-colors hover:bg-[var(--bg-tertiary)]"
                >
                  <span className="truncate text-[var(--text-primary)]">
                    {company.name}
                  </span>
                  <span className="ml-2 shrink-0 text-xs text-[var(--text-muted)]">
                    {company.article_count}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
