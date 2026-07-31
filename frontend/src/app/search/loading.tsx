export default function SearchLoading() {
  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="mb-8 h-11 max-w-2xl animate-pulse rounded-xl bg-[var(--bg-secondary)]" />
      <div className="mb-4 h-4 w-40 animate-pulse rounded bg-[var(--bg-secondary)]" />
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5"
          >
            <div className="mb-3 h-3 w-32 rounded bg-[var(--bg-tertiary)]" />
            <div className="mb-2 h-4 w-3/4 rounded bg-[var(--bg-tertiary)]" />
            <div className="h-3 w-full rounded bg-[var(--bg-tertiary)]" />
          </div>
        ))}
      </div>
    </div>
  );
}
