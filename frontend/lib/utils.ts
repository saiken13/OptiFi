import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function getInitials(name: string | null | undefined): string {
  if (!name) return "U";
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export const CATEGORIES = [
  "dining",
  "groceries",
  "gas",
  "travel",
  "shopping",
  "entertainment",
  "health",
  "utilities",
  "subscriptions",
  "other",
] as const;

export const CATEGORY_COLORS: Record<string, string> = {
  dining: "#f97316",
  groceries: "#22c55e",
  gas: "#eab308",
  travel: "#3b82f6",
  shopping: "#8b5cf6",
  entertainment: "#ec4899",
  health: "#14b8a6",
  utilities: "#64748b",
  subscriptions: "#6366f1",
  other: "#94a3b8",
};

export const AGENT_LABELS: Record<string, string> = {
  budget: "Budget",
  goal: "Goals",
  loan: "Loans",
  purchase_optimize: "Purchase",
  weekly_review: "Weekly Review",
  card_import: "Card Import",
  tax: "Tax",
  general: "General",
};
