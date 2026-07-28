import { Newspaper } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--bg-secondary)] px-6 py-16 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--bg-tertiary)]">
        <Newspaper className="h-6 w-6 text-[var(--text-muted)]" />
      </div>
      <h3 className="text-base font-medium text-[var(--text-primary)]">
        {title}
      </h3>
      <p className="mt-2 max-w-sm text-sm text-[var(--text-secondary)]">
        {description}
      </p>
    </div>
  );
}
