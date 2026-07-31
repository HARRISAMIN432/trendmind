export default function TrendDetailLoading() {
  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="mb-6 h-4 w-48 animate-pulse rounded bg-[var(--bg-secondary)]" />
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5"
          >
            <div className="mb-2 h-4 w-3/4 rounded bg-[var(--bg-tertiary)]" />
            <div className="h-3 w-full rounded bg-[var(--bg-tertiary)]" />
          </div>
        ))}
      </div>
    </div>
  );
}
