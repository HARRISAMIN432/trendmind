import { Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { RightPanel } from "@/components/layout/RightPanel";
import { NewsFeed } from "@/components/NewsFeed";
import { fetchArticles } from "@/lib/api";
import { ARTICLES_PER_PAGE } from "@/lib/constants";

interface HomePageProps {
  searchParams: Promise<{
    category?: string;
    importance?: string;
    offset?: string;
  }>;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const category = params.category ?? null;
  const importance = params.importance ?? null;
  const offset = Number(params.offset ?? 0);

  let data;
  try {
    data = await fetchArticles({
      limit: ARTICLES_PER_PAGE,
      offset,
      category: category ?? undefined,
      importance: importance ?? undefined,
    });
  } catch {
    data = { total: 0, limit: ARTICLES_PER_PAGE, offset: 0, items: [] };
  }

  const greeting = getGreeting();

  return (
    <AppShell rightPanel={<RightPanel />}>
      <Header
        title={`${greeting}`}
        subtitle="Curated AI news from RSS feeds, classified and summarized by a multi-agent pipeline."
        showSearch
      />
      <Suspense
        fallback={
          <div className="px-6 py-12 text-sm text-[var(--text-muted)]">
            Loading feed...
          </div>
        }
      >
        <NewsFeed
          initialData={data}
          initialCategory={category}
          initialImportance={importance}
          initialOffset={offset}
        />
      </Suspense>
    </AppShell>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
