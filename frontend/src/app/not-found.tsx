import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";

export default function NotFound() {
  return (
    <AppShell>
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <p className="text-6xl font-semibold text-[var(--accent)]">404</p>
        <h1 className="mt-4 text-xl font-semibold text-[var(--text-primary)]">
          Page not found
        </h1>
        <p className="mt-2 max-w-md text-sm text-[var(--text-secondary)]">
          The page you are looking for does not exist or the resource could not
          be loaded.
        </p>
        <Link
          href="/"
          className="mt-6 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)]"
        >
          Back to home
        </Link>
      </div>
    </AppShell>
  );
}
