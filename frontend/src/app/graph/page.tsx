import { AppShell } from "@/components/layout/AppShell";
import { Header } from "@/components/layout/Header";
import { KnowledgeGraphViz } from "@/components/KnowledgeGraphViz";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchGraph } from "@/lib/api";
import { NODE_TYPE_COLORS } from "@/lib/constants";

export const metadata = {
  title: "Knowledge Graph",
};

export default async function GraphPage() {
  let graph;
  try {
    graph = await fetchGraph();
  } catch {
    graph = { nodes: [], edges: [] };
  }

  const typeCounts = graph.nodes.reduce<Record<string, number>>((acc, node) => {
    acc[node.type] = (acc[node.type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <AppShell>
      <Header
        title="Knowledge Graph"
        subtitle="Entities and relationships extracted from AI news articles."
      />

      <div className="px-4 py-4 sm:px-6 sm:py-6">
        {graph.nodes.length === 0 ? (
          <EmptyState
            title="Graph is empty"
            description="Nothing to show for now"
          />
        ) : (
          <>
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
              <p className="text-sm text-[var(--text-muted)]">
                {graph.nodes.length} nodes · {graph.edges.length} edges
              </p>
              <div className="flex flex-wrap gap-3">
                {Object.entries(typeCounts).map(([type, count]) => (
                  <span
                    key={type}
                    className="inline-flex items-center gap-1.5 text-xs text-[var(--text-secondary)]"
                  >
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{
                        backgroundColor: NODE_TYPE_COLORS[type] ?? "#71717A",
                      }}
                    />
                    {type} ({count})
                  </span>
                ))}
              </div>
            </div>

            <div className="h-[60vh] min-h-[360px] overflow-hidden rounded-xl border border-[var(--border)] sm:h-[calc(100vh-220px)] sm:min-h-[480px]">
              <KnowledgeGraphViz nodes={graph.nodes} edges={graph.edges} />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
