import { Sidebar } from "./Sidebar";
import { MobileTopBar } from "./MobileTopbar";
import { SidebarProvider } from "./SidebarContext";
import { SidebarBackdrop } from "./SidebarBackdrop";

interface AppShellProps {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
}

export function AppShell({ children, rightPanel }: AppShellProps) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen bg-[var(--bg-primary)]">
        <Sidebar />
        <SidebarBackdrop />

        <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
          <MobileTopBar />

          <div className="flex min-w-0 flex-1">
            <main className="min-w-0 flex-1">{children}</main>
            {rightPanel && (
              <aside className="hidden w-80 shrink-0 border-l border-[var(--border)] bg-[var(--bg-secondary)] xl:block">
                {rightPanel}
              </aside>
            )}
          </div>
        </div>
      </div>
    </SidebarProvider>
  );
}
