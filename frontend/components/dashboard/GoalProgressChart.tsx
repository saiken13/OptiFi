"use client";

import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from "recharts";
import { formatCurrency } from "@/lib/utils";
import type { Goal } from "@/types";

interface Props {
  goals: Goal[];
}

const COLORS = ["#3b82f6", "#22c55e", "#f97316", "#8b5cf6", "#ec4899"];

export function GoalProgressChart({ goals }: Props) {
  if (goals.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        No active goals
      </div>
    );
  }

  const data = goals.slice(0, 5).map((g, i) => ({
    name: g.name,
    value: Math.round((g.current_amount / g.target_amount) * 100),
    fill: COLORS[i % COLORS.length],
    current: g.current_amount,
    target: g.target_amount,
  }));

  return (
    <div className="space-y-3">
      {goals.slice(0, 4).map((g, i) => {
        const pct = Math.min(100, (g.current_amount / g.target_amount) * 100);
        return (
          <div key={g.id}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium truncate max-w-[120px]">{g.name}</span>
              <span className="text-xs text-muted-foreground">
                {formatCurrency(g.current_amount)} / {formatCurrency(g.target_amount)}
              </span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
