export default function CompaniesLoading() {
  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 9 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4"
          >
            <div className="mb-3 h-4 w-2/3 rounded bg-[var(--bg-tertiary)]" />
            <div className="h-3 w-1/3 rounded bg-[var(--bg-tertiary)]" />
          </div>
        ))}
      </div>
    </div>
  );
}
