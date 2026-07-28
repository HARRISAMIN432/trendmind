export const CATEGORIES = [
  "Research",
  "Product Launch",
  "Funding",
  "Policy & Regulation",
  "Business & Industry",
  "Open Source",
  "Opinion & Analysis",
  "Other",
] as const;

export const IMPORTANCE_LEVELS = ["High", "Medium", "Low"] as const;

export const ARTICLES_PER_PAGE = 12;

export const NODE_TYPE_COLORS: Record<string, string> = {
  Company: "#7C3AED",
  Model: "#6366F1",
  Researcher: "#22C55E",
  Dataset: "#F59E0B",
  Product: "#3B82F6",
};
