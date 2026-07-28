"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  initialQuery?: string;
  autoFocus?: boolean;
  size?: "default" | "large";
  onSearch?: (query: string) => void;
}

export function SearchBar({
  initialQuery = "",
  autoFocus = false,
  size = "default",
  onSearch,
}: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    if (onSearch) {
      onSearch(trimmed);
    } else {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <Search
          className={cn(
            "absolute top-1/2 -translate-y-1/2 text-[var(--text-muted)]",
            size === "large" ? "left-4 h-5 w-5" : "left-3 h-4 w-4",
          )}
        />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by meaning, not just keywords..."
          autoFocus={autoFocus}
          className={cn(
            "w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)]",
            size === "large"
              ? "py-4 pl-12 pr-4 text-base"
              : "py-2.5 pl-10 pr-4 text-sm",
          )}
        />
      </div>
    </form>
  );
}
