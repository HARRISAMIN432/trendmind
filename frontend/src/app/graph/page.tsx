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

      <div className="px-6 py-6">
        {graph.nodes.length === 0 ? (
          <EmptyState
            title="Graph is empty"
            description="Build the knowledge graph via POST /graph/build on the backend. The scheduler (M21) can automate this."
          />
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center gap-4">
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
                      className="h-2.5 w-2.5 rounded-full"
                      style={{
                        backgroundColor: NODE_TYPE_COLORS[type] ?? "#71717A",
                      }}
                    />
                    {type} ({count})
                  </span>
                ))}
              </div>
            </div>

            <div className="h-[calc(100vh-220px)] min-h-[480px] overflow-hidden rounded-xl border border-[var(--border)]">
              <KnowledgeGraphViz nodes={graph.nodes} edges={graph.edges} />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
