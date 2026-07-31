import { Loader2 } from "lucide-react";

export default function GraphLoading() {
  return (
    <div className="px-4 py-4 sm:px-6 sm:py-6">
      <div className="flex h-[60vh] min-h-[360px] flex-col items-center justify-center gap-3 rounded-xl border border-[var(--border)] sm:h-[calc(100vh-220px)] sm:min-h-[480px]">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--accent)]" />
        <p className="text-sm text-[var(--text-muted)]">
          Building knowledge graph…
        </p>
      </div>
    </div>
  );
}
