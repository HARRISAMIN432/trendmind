export default function ArticleLoading() {
  return (
    <div className="grid gap-6 px-4 py-4 sm:gap-8 sm:px-6 sm:py-6 lg:grid-cols-[1fr_380px]">
      <div className="animate-pulse space-y-4">
        <div className="h-3 w-40 rounded bg-[var(--bg-secondary)]" />
        <div className="h-7 w-full rounded bg-[var(--bg-secondary)]" />
        <div className="h-7 w-2/3 rounded bg-[var(--bg-secondary)]" />
        <div className="mt-6 h-24 w-full rounded bg-[var(--bg-secondary)]" />
      </div>
      <div className="h-[420px] animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)]" />
    </div>
  );
}
