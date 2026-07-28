import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { SearchResultsView } from "@/components/SearchResultsView";
import { searchArticles } from "@/lib/api";

export const metadata = {
  title: "Search",
};

interface SearchPageProps {
  searchParams: Promise<{ q?: string }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";

  let results: Awaited<ReturnType<typeof searchArticles>>["results"] = [];
  let error: string | null = null;

  if (query) {
    try {
      const response = await searchArticles(query, 20);
      results = response.results;
    } catch {
      error = "Search failed. Ensure the backend is running.";
    }
  }

  return (
    <AppShell>
      <Header
        title="Search"
        subtitle="Natural-language semantic search across your AI news corpus."
      />
      <SearchResultsView query={query} results={results} error={error} />
    </AppShell>
  );
}
