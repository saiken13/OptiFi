"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { formatCurrency } from "@/lib/utils";
import { loan_amortization } from "@/lib/loanUtils";
import type { Loan } from "@/types";

interface Props {
  loans: Loan[];
}

export function LoanPayoffChart({ loans }: Props) {
  if (loans.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        No loans tracked
      </div>
    );
  }

  // Pick the largest loan for the chart
  const loan = loans.reduce((a, b) =>
    a.current_balance > b.current_balance ? a : b
  );

  const schedule = loan_amortization(
    loan.current_balance,
    loan.interest_rate,
    loan.monthly_payment,
    loan.extra_payment
  );

  const scheduleNoExtra = loan.extra_payment > 0
    ? loan_amortization(loan.current_balance, loan.interest_rate, loan.monthly_payment, 0)
    : schedule;

  // Sample every 6 months for the chart
  const chartData = schedule
    .filter((_, i) => i % 6 === 0 || i === schedule.length - 1)
    .map((entry, i) => {
      const noExtraEntry = scheduleNoExtra[Math.min(entry.month - 1, scheduleNoExtra.length - 1)];
      return {
        month: `Mo ${entry.month}`,
        withExtra: entry.balance,
        standard: noExtraEntry?.balance ?? 0,
      };
    });

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          axisLine={false}
          tickLine={false}
          width={44}
        />
        <Tooltip
          formatter={(value: number) => [formatCurrency(value), ""]}
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            fontSize: "11px",
          }}
        />
        {loan.extra_payment > 0 && (
          <Line
            type="monotone"
            dataKey="standard"
            stroke="hsl(var(--muted-foreground))"
            strokeDasharray="4 4"
            dot={false}
            name="Standard"
            strokeWidth={1.5}
          />
        )}
        <Line
          type="monotone"
          dataKey="withExtra"
          stroke="#3b82f6"
          dot={false}
          name={loan.extra_payment > 0 ? "With extra" : loan.name}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
