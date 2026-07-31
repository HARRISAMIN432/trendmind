"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  GitBranch,
  Home,
  Network,
  Search,
  TrendingUp,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebar } from "./SidebarContext";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/search", label: "Search", icon: Search },
  { href: "/trends", label: "Trends", icon: TrendingUp },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/graph", label: "Knowledge Graph", icon: Network },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isOpen, close } = useSidebar();

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex h-screen w-64 shrink-0 flex-col overflow-y-auto border-r border-[var(--border)] bg-[var(--bg-secondary)] transition-transform duration-200 ease-out",
        // Mobile: off-canvas drawer, slides in/out based on isOpen.
        isOpen ? "translate-x-0" : "-translate-x-full",
        // Desktop: always fixed and visible, ignore drawer state entirely.
        "lg:translate-x-0",
      )}
    >
      <div className="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
        <Image
          src="/logo.png"
          alt="DigestAI"
          width={36}
          height={36}
          className="h-9 w-9 shrink-0 rounded-lg"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
            DigestAI
          </p>
          <p className="truncate text-xs text-[var(--text-muted)]">
            AI News Intelligence
          </p>
        </div>
        <button
          type="button"
          onClick={close}
          aria-label="Close menu"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] lg:hidden"
        >
          <X className="h-4 w-4" />
        </button>
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
              onClick={close}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-[var(--accent-muted)] font-semibold text-[var(--accent)] ring-1 ring-inset ring-[var(--accent)]/20"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
