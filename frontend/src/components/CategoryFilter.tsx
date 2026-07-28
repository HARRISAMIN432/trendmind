"use client";

import { CATEGORIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface CategoryFilterProps {
  selected: string | null;
  onChange: (category: string | null) => void;
}

export function CategoryFilter({ selected, onChange }: CategoryFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        onClick={() => onChange(null)}
        className={cn(
          "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
          selected === null
            ? "bg-[var(--accent)] text-white"
            : "bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
        )}
      >
        All
      </button>
      {CATEGORIES.map((category) => (
        <button
          key={category}
          type="button"
          onClick={() => onChange(category)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            selected === category
              ? "bg-[var(--accent)] text-white"
              : "bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
          )}
        >
          {category}
        </button>
      ))}
    </div>
  );
}

interface ImportanceFilterProps {
  selected: string | null;
  onChange: (importance: string | null) => void;
}

const IMPORTANCE_OPTIONS = ["High", "Medium", "Low"] as const;

export function ImportanceFilter({
  selected,
  onChange,
}: ImportanceFilterProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-[var(--text-muted)]">Importance</span>
      <select
        value={selected ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
      >
        <option value="">Any</option>
        {IMPORTANCE_OPTIONS.map((level) => (
          <option key={level} value={level}>
            {level}
          </option>
        ))}
      </select>
    </div>
  );
}
