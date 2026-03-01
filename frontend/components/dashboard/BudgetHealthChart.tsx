"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { formatCurrency, CATEGORY_COLORS } from "@/lib/utils";

interface BudgetItem {
  category: string;
  limit: number;
  spent: number;
  percent_used: number;
  status: "ok" | "warning" | "over";
}

interface Props {
  data: BudgetItem[];
}

const STATUS_COLORS = {
  ok: "#22c55e",
  warning: "#eab308",
  over: "#ef4444",
};

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: BudgetItem }> }) => {
  if (!active || !payload?.[0]) return null;
  const item = payload[0].payload;
  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold capitalize mb-1">{item.category}</p>
      <p>Spent: {formatCurrency(item.spent)}</p>
      <p>Limit: {formatCurrency(item.limit)}</p>
      <p className={item.status === "over" ? "text-red-400" : item.status === "warning" ? "text-yellow-400" : "text-green-400"}>
        {item.percent_used.toFixed(0)}% used
      </p>
    </div>
  );
};

export function BudgetHealthChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        No budget data for this month
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="category"
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickFormatter={(v) => v.slice(0, 8)}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickFormatter={(v) => `$${v}`}
          axisLine={false}
          tickLine={false}
          width={48}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--accent))" }} />
        <Legend
          formatter={(value) => (
            <span style={{ fontSize: 11, color: "hsl(var(--muted-foreground))" }}>
              {value === "limit" ? "Limit" : "Spent"}
            </span>
          )}
        />
        <Bar dataKey="limit" radius={[4, 4, 0, 0]} name="limit">
          {data.map((entry, i) => (
            <Cell key={i} fill={CATEGORY_COLORS[entry.category] || "#94a3b8"} opacity={0.35} />
          ))}
        </Bar>
        <Bar dataKey="spent" radius={[4, 4, 0, 0]} name="spent">
          {data.map((entry, i) => (
            <Cell key={i} fill={STATUS_COLORS[entry.status]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
