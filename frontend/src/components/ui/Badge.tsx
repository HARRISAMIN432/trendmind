import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "accent" | "outline" | "muted";
  className?: string;
}

export function Badge({
  children,
  variant = "outline",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        variant === "default" && "bg-[var(--bg-elevated)] text-[var(--text-secondary)]",
        variant === "accent" && "bg-[var(--accent-muted)] text-[var(--accent)]",
        variant === "outline" &&
          "border border-[var(--border)] text-[var(--text-secondary)]",
        variant === "muted" && "text-[var(--text-muted)]",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ImportanceBadge({ importance }: { importance: string | null }) {
  if (!importance) return null;

  const variant =
    importance === "High"
      ? "accent"
      : importance === "Medium"
        ? "outline"
        : "muted";

  return <Badge variant={variant}>{importance}</Badge>;
}
