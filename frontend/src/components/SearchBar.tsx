"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  initialQuery?: string;
  autoFocus?: boolean;
  size?: "default" | "large";
  onSearch?: (query: string) => void;
  loading?: boolean;
}

export function SearchBar({
  initialQuery = "",
  autoFocus = false,
  size = "default",
  onSearch,
  loading = false,
}: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [isPending, startTransition] = useTransition();

  const isSearching = loading || isPending;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    if (onSearch) {
      onSearch(trimmed);
    } else {
      startTransition(() => {
        router.push(`/search?q=${encodeURIComponent(trimmed)}`);
      });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full" aria-busy={isSearching}>
      <div className="relative">
        {isSearching ? (
          <Loader2
            className={cn(
              "absolute top-1/2 -translate-y-1/2 animate-spin text-[var(--accent)]",
              size === "large" ? "left-4 h-5 w-5" : "left-3 h-4 w-4",
            )}
          />
        ) : (
          <Search
            className={cn(
              "absolute top-1/2 -translate-y-1/2 text-[var(--text-muted)]",
              size === "large" ? "left-4 h-5 w-5" : "left-3 h-4 w-4",
            )}
          />
        )}
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by meaning, not just keywords..."
          autoFocus={autoFocus}
          disabled={isSearching}
          className={cn(
            "w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] disabled:opacity-70",
            size === "large"
              ? "py-4 pl-12 pr-4 text-base"
              : "py-2.5 pl-10 pr-4 text-sm",
          )}
        />
      </div>
      <span className="sr-only" role="status">
        {isSearching ? "Searching…" : ""}
      </span>
    </form>
  );
}
