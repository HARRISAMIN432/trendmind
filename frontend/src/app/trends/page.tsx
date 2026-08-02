import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { fetchTrends } from "@/lib/api";
import { TrendsList } from "@/components/trends/trendsList";

export const metadata = {
  title: "Trends",
};

const PAGE_SIZE = 20;

export default async function TrendsPage() {
  let data;
  try {
    data = await fetchTrends(PAGE_SIZE, 0);
  } catch {
    data = { total: 0, limit: PAGE_SIZE, offset: 0, items: [] };
  }

  return (
    <AppShell>
      <Header title="Trends" subtitle="" />

      <div className="px-4 py-4 sm:px-6 sm:py-6">
        <TrendsList initialData={data} />
      </div>
    </AppShell>
  );
}
