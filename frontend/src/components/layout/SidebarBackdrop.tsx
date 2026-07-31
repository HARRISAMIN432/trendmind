"use client";

import { useSidebar } from "./SidebarContext";
import { cn } from "@/lib/utils";

export function SidebarBackdrop() {
  const { isOpen, close } = useSidebar();

  return (
    <div
      onClick={close}
      aria-hidden="true"
      className={cn(
        "fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-200 lg:hidden",
        isOpen
          ? "pointer-events-auto opacity-100"
          : "pointer-events-none opacity-0",
      )}
    />
  );
}
