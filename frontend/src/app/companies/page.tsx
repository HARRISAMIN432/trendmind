import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchCompanies } from "@/lib/api";
import { encodeCompanyName } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

export const metadata = {
  title: "Companies",
};

export default async function CompaniesPage() {
  let data;
  try {
    data = await fetchCompanies(100, 0);
  } catch {
    data = { total: 0, limit: 100, offset: 0, items: [] };
  }

  return (
    <AppShell>
      <Header
        title="Companies"
        subtitle="Organizations mentioned across ingested AI news articles."
      />

      <div className="px-6 py-6">
        {data.items.length === 0 ? (
          <EmptyState
            title="No companies tracked"
            description="Companies are extracted during article classification. Run the ingestion pipeline to populate this list."
          />
        ) : (
          <div className="space-y-2">
            <p className="mb-4 text-sm text-[var(--text-muted)]">
              {data.total} {data.total === 1 ? "company" : "companies"} tracked
            </p>
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
        )}
      </div>
    </AppShell>
  );
}
