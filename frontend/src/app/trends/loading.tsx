export default function TrendsLoading() {
  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5"
          >
            <div className="mb-2 h-4 w-2/3 rounded bg-[var(--bg-tertiary)]" />
            <div className="h-3 w-1/2 rounded bg-[var(--bg-tertiary)]" />
          </div>
        ))}
      </div>
    </div>
  );
}
