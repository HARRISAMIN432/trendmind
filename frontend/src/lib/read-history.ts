const STORAGE_KEY = "trendmind-read-urls";
const MAX_ITEMS = 50;

export function getReadUrls(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as string[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addReadUrl(url: string): void {
  if (typeof window === "undefined" || !url) return;
  const current = getReadUrls().filter((item) => item !== url);
  current.unshift(url);
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(current.slice(0, MAX_ITEMS)),
  );
}
