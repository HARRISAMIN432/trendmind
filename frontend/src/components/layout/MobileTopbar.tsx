"use client";

import Image from "next/image";
import { Menu } from "lucide-react";
import { useSidebar } from "./SidebarContext";

export function MobileTopBar() {
  const { toggle, isOpen } = useSidebar();

  return (
    <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-[var(--border)] bg-[var(--bg-primary)] px-4 py-3 lg:hidden">
      <button
        type="button"
        onClick={toggle}
        aria-label={isOpen ? "Close menu" : "Open menu"}
        aria-expanded={isOpen}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
      >
        <Menu className="h-5 w-5" />
      </button>
      <Image
        src="/logo.png"
        alt="DigestAI"
        width={28}
        height={28}
        className="h-7 w-7 shrink-0 rounded-md"
      />
      <p className="text-sm font-semibold text-[var(--text-primary)]">
        DigestAI
      </p>
    </div>
  );
}
