"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MessageSquare, TrendingDown, Target, PiggyBank, ArrowRight, RefreshCw } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { BudgetHealthChart } from "@/components/dashboard/BudgetHealthChart";
import { GoalProgressChart } from "@/components/dashboard/GoalProgressChart";
import { LoanPayoffChart } from "@/components/dashboard/LoanPayoffChart";
import { budgetsApi, goalsApi, loansApi, transactionsApi, weeklyReviewApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { Budget, Goal, Loan } from "@/types";

function StatCard({
  label,
  value,
  sub,
  color = "text-foreground",
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();

  const { data: budgets = [] } = useQuery<Budget[]>({
    queryKey: ["budgets"],
    queryFn: () => budgetsApi.list().then((r) => r.data),
  });

  const { data: goals = [] } = useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => goalsApi.list().then((r) => r.data),
  });

  const { data: loans = [] } = useQuery<Loan[]>({
    queryKey: ["loans"],
    queryFn: () => loansApi.list().then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ["txn-summary"],
    queryFn: () => transactionsApi.summary().then((r) => r.data),
  });

  const totalDebt = loans.reduce((s, l) => s + l.current_balance, 0);
  const totalGoalProgress =
    goals.length > 0
      ? goals.reduce((s, g) => s + (g.current_amount / g.target_amount) * 100, 0) / goals.length
      : 0;

  const budgetHealth = budgets.map((b) => ({
    category: b.category,
    limit: b.monthly_limit,
    spent: b.spent_this_month,
    percent_used: b.monthly_limit > 0 ? (b.spent_this_month / b.monthly_limit) * 100 : 0,
    status: (b.monthly_limit > 0
      ? b.spent_this_month / b.monthly_limit > 1
        ? "over"
        : b.spent_this_month / b.monthly_limit > 0.8
        ? "warning"
        : "ok"
      : "ok") as "ok" | "warning" | "over",
  }));

  const reviewMutation = useMutation({
    mutationFn: () => weeklyReviewApi.run(),
    onSuccess: () => router.push("/weekly-review"),
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dashboard"
        subtitle="Your financial overview"
        actions={
          <button
            onClick={() => reviewMutation.mutate()}
            disabled={reviewMutation.isPending}
            className="flex items-center gap-1.5 text-xs bg-primary/10 text-primary px-3 py-1.5 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${reviewMutation.isPending ? "animate-spin" : ""}`} />
            {reviewMutation.isPending ? "Generating..." : "Weekly Review"}
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Monthly Expenses"
            value={formatCurrency(summary?.total_expenses || 0)}
            sub={summary ? `Net: ${formatCurrency(summary.net)}` : undefined}
          />
          <StatCard
            label="Total Debt"
            value={formatCurrency(totalDebt)}
            sub={`${loans.length} loan${loans.length !== 1 ? "s" : ""}`}
            color={totalDebt > 0 ? "text-red-400" : "text-green-400"}
          />
          <StatCard
            label="Goal Progress"
            value={`${totalGoalProgress.toFixed(0)}%`}
            sub={`${goals.length} active goal${goals.length !== 1 ? "s" : ""}`}
            color="text-blue-400"
          />
          <StatCard
            label="Active Budgets"
            value={`${budgets.length}`}
            sub={`${budgetHealth.filter((b) => b.status === "over").length} over limit`}
            color={budgetHealth.some((b) => b.status === "over") ? "text-red-400" : "text-green-400"}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Budget Health</h3>
              <Link href="/budgets" className="text-xs text-primary flex items-center gap-1 hover:underline">
                Manage <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <BudgetHealthChart data={budgetHealth} />
          </div>

          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Goal Progress</h3>
              <Link href="/goals" className="text-xs text-primary flex items-center gap-1 hover:underline">
                Manage <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <GoalProgressChart goals={goals} />
          </div>

          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Loan Payoff Curve</h3>
              <Link href="/loans" className="text-xs text-primary flex items-center gap-1 hover:underline">
                Manage <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <LoanPayoffChart loans={loans} />
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Link
            href="/chat"
            className="flex items-center gap-3 bg-primary/10 border border-primary/20 rounded-xl p-4 hover:bg-primary/20 transition-colors"
          >
            <MessageSquare className="h-5 w-5 text-primary shrink-0" />
            <div>
              <p className="text-sm font-medium">Chat with AI</p>
              <p className="text-xs text-muted-foreground">Ask anything about your finances</p>
            </div>
          </Link>
          <Link
            href="/purchase"
            className="flex items-center gap-3 bg-green-500/10 border border-green-500/20 rounded-xl p-4 hover:bg-green-500/20 transition-colors"
          >
            <TrendingDown className="h-5 w-5 text-green-500 shrink-0" />
            <div>
              <p className="text-sm font-medium">Purchase Optimizer</p>
              <p className="text-xs text-muted-foreground">Find the best price + card combo</p>
            </div>
          </Link>
          <Link
            href="/cards"
            className="flex items-center gap-3 bg-purple-500/10 border border-purple-500/20 rounded-xl p-4 hover:bg-purple-500/20 transition-colors"
          >
            <PiggyBank className="h-5 w-5 text-purple-500 shrink-0" />
            <div>
              <p className="text-sm font-medium">Import Card Rewards</p>
              <p className="text-xs text-muted-foreground">AI-powered card data extraction</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
