export default function CompanyLoading() {
  return (
    <div className="space-y-8 px-4 py-4 sm:px-6 sm:py-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3"
          >
            <div className="mb-2 h-3 w-16 rounded bg-[var(--bg-tertiary)]" />
            <div className="h-5 w-20 rounded bg-[var(--bg-tertiary)]" />
          </div>
        ))}
      </div>
      <div className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
        <div className="h-3 w-full rounded bg-[var(--bg-tertiary)]" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
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
