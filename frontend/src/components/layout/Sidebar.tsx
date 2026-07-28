"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  GitBranch,
  Home,
  Network,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/search", label: "Search", icon: Search },
  { href: "/trends", label: "Trends", icon: TrendingUp },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/graph", label: "Knowledge Graph", icon: Network },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            TrendMind
          </p>
          <p className="text-xs text-[var(--text-muted)]">AI News Intelligence</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/"
              ? pathname === "/"
              : pathname === href || pathname.startsWith(`${href}/`);

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border)] p-4">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-tertiary)] p-4">
          <div className="mb-2 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-[var(--accent)]" />
            <p className="text-xs font-medium text-[var(--text-primary)]">
              Multi-Agent Pipeline
            </p>
          </div>
          <p className="text-xs leading-relaxed text-[var(--text-muted)]">
            LangGraph ingestion, RAG chat, and semantic search over curated AI
            news.
          </p>
        </div>
      </div>
    </aside>
  );
}
