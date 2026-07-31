"use client";

import { Check } from "lucide-react";
import { CATEGORIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface CategoryFilterProps {
  selected: string | null;
  onChange: (category: string | null) => void;
}

export function CategoryFilter({ selected, onChange }: CategoryFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <FilterChip
        label="All"
        active={selected === null}
        onClick={() => onChange(null)}
      />
      {CATEGORIES.map((category) => (
        <FilterChip
          key={category}
          label={category}
          active={selected === category}
          onClick={() => onChange(category)}
        />
      ))}
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all",
        active
          ? "border-[var(--accent)] bg-[var(--accent)] text-white shadow-sm ring-2 ring-[var(--accent)]/30 ring-offset-1 ring-offset-[var(--bg-primary)]"
          : "border-transparent bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:border-[var(--border)] hover:text-[var(--text-primary)]",
      )}
    >
      {active && <Check className="h-3.5 w-3.5" />}
      {label}
    </button>
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
        className={cn(
          "rounded-lg border bg-[var(--bg-secondary)] px-3 py-1.5 text-sm outline-none transition-colors focus:border-[var(--accent)]",
          selected
            ? "border-[var(--accent)] font-medium text-[var(--text-primary)]"
            : "border-[var(--border)] text-[var(--text-primary)]",
        )}
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
