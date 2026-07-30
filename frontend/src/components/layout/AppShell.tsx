import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
}

export function AppShell({ children, rightPanel }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 pl-64">
        <main className="min-w-0 flex-1">{children}</main>
        {rightPanel && (
          <aside className="hidden w-80 shrink-0 border-l border-[var(--border)] bg-[var(--bg-secondary)] xl:block">
            {rightPanel}
          </aside>
        )}
      </div>
    </div>
  );
}
