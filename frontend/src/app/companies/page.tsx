import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { fetchCompanies } from "@/lib/api";
import { CompaniesList } from "@/components/companies/CompaniesList";

export const metadata = {
  title: "Companies",
};

const PAGE_SIZE = 20;

export default async function CompaniesPage() {
  let data;
  try {
    data = await fetchCompanies(PAGE_SIZE, 0);
  } catch {
    data = { total: 0, limit: PAGE_SIZE, offset: 0, items: [] };
  }

  return (
    <AppShell>
      <Header
        title="Companies"
        subtitle="Organizations mentioned across ingested AI news articles."
      />

      <div className="px-4 py-4 sm:px-6 sm:py-6">
        <CompaniesList initialData={data} />
      </div>
    </AppShell>
  );
}
