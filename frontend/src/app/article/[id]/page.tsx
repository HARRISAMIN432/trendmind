import { ArticleDetailView } from "@/components/ArticleDetailView";
import { fetchArticle } from "@/lib/api";
import type { ArticleDetail } from "@/lib/types";
import { notFound } from "next/navigation";

interface ArticlePageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: ArticlePageProps) {
  const { id } = await params;
  try {
    const article = await fetchArticle(Number(id));
    return { title: article.title };
  } catch {
    return { title: "Article" };
  }
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { id } = await params;
  const articleId = Number(id);

  if (Number.isNaN(articleId)) notFound();

  let article: ArticleDetail | null = null;
  try {
    article = await fetchArticle(articleId);
  } catch {
    notFound();
  }

  if (!article) notFound();

  return <ArticleDetailView article={article} />;
}
