"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Loader2, Calendar, TrendingDown, TrendingUp, AlertTriangle, Mail } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { weeklyReviewApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface StructuredData {
  week: string;
  total_expenses_this_week: number;
  total_income_this_week: number;
  net_this_week: number;
  spending_by_category: Record<string, number>;
  transaction_count: number;
  budget_warnings: string[];
  active_goals: number;
  total_goal_progress: number;
  total_debt: number;
}

interface WeeklyReview {
  id: string;
  week_start: string;
  week_end: string;
  summary: string;
  structured_data: StructuredData | null;
  created_at?: string;
}

function ReviewContent({ review }: { review: WeeklyReview }) {
  const sd = review.structured_data;

  return (
    <div className="space-y-4">
      {/* Week header */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Calendar className="h-4 w-4" />
        <span>{review.week_start} — {review.week_end}</span>
        {review.created_at && (
          <span className="ml-auto text-xs">Generated {new Date(review.created_at).toLocaleString()}</span>
        )}
      </div>

      {/* Stats */}
      {sd && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-card border border-border rounded-xl p-3">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingDown className="h-3 w-3" /> Weekly Expenses
            </p>
            <p className="text-lg font-bold text-red-400 mt-1">{formatCurrency(sd.total_expenses_this_week)}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-3">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3" /> Weekly Income
            </p>
            <p className="text-lg font-bold text-green-400 mt-1">{formatCurrency(sd.total_income_this_week)}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-3">
            <p className="text-xs text-muted-foreground">Net This Week</p>
            <p className={`text-lg font-bold mt-1 ${sd.net_this_week >= 0 ? "text-green-400" : "text-red-400"}`}>
              {formatCurrency(sd.net_this_week)}
            </p>
          </div>
          <div className="bg-card border border-border rounded-xl p-3">
            <p className="text-xs text-muted-foreground">Transactions</p>
            <p className="text-lg font-bold mt-1">{sd.transaction_count}</p>
          </div>
        </div>
      )}

      {/* Budget warnings */}
      {sd && sd.budget_warnings.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <h3 className="text-sm font-semibold text-red-400">Budget Alerts</h3>
          </div>
          <ul className="space-y-1">
            {sd.budget_warnings.map((w, i) => (
              <li key={i} className="text-xs text-muted-foreground">• {w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Spending by category */}
      {sd && Object.keys(sd.spending_by_category).length > 0 && (
        <div className="bg-card border border-border rounded-xl p-4">
          <h3 className="text-sm font-semibold mb-3">Spending by Category</h3>
          <div className="space-y-2">
            {Object.entries(sd.spending_by_category)
              .sort(([, a], [, b]) => b - a)
              .map(([cat, amt]) => (
                <div key={cat} className="flex justify-between text-xs">
                  <span className="capitalize text-muted-foreground">{cat}</span>
                  <span className="font-medium">{formatCurrency(amt)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* AI Summary */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-3">AI Analysis</h3>
        <div className="prose prose-invert prose-sm max-w-none">
          {review.summary.split("\n").map((line, i) => {
            if (line.startsWith("## ")) {
              return <h3 key={i} className="text-sm font-bold mt-4 mb-1 text-foreground">{line.replace("## ", "")}</h3>;
            }
            if (line.startsWith("**") && line.endsWith("**")) {
              return <p key={i} className="text-sm font-semibold text-foreground mt-2">{line.replace(/\*\*/g, "")}</p>;
            }
            if (line.startsWith("- ") || line.startsWith("• ")) {
              return <p key={i} className="text-sm text-muted-foreground pl-3">• {line.slice(2)}</p>;
            }
            if (line.trim() === "") return <div key={i} className="h-2" />;
            return <p key={i} className="text-sm text-muted-foreground leading-relaxed">{line}</p>;
          })}
        </div>
      </div>
    </div>
  );
}

export default function WeeklyReviewPage() {
  const [emailSent, setEmailSent] = useState(false);
  const qc = useQueryClient();

  const { data: latest, isLoading } = useQuery<WeeklyReview>({
    queryKey: ["weekly-review-latest"],
    queryFn: () => weeklyReviewApi.latest().then((r) => r.data),
    retry: false,
  });

  const runMutation = useMutation({
    mutationFn: () => weeklyReviewApi.run().then((r) => r.data),
    onSuccess: () => {
      setEmailSent(true);
      qc.invalidateQueries({ queryKey: ["weekly-review-latest"] });
      setTimeout(() => setEmailSent(false), 4000);
    },
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Weekly Review"
        subtitle="Your AI-generated weekly financial summary"
        actions={
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {runMutation.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
            {runMutation.isPending ? "Generating..." : "Run New Review"}
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {emailSent && (
          <div className="flex items-center gap-2 mb-4 bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3 text-sm text-green-400">
            <Mail className="h-4 w-4" />
            Review generated! Email sent to your account (if SMTP is configured).
          </div>
        )}

        {runMutation.isPending && (
          <div className="flex flex-col items-center justify-center h-48 space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm font-medium">Generating your weekly review...</p>
            <p className="text-xs text-muted-foreground">Analyzing transactions, budgets, goals and loans</p>
          </div>
        )}

        {!runMutation.isPending && isLoading && (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {!runMutation.isPending && !isLoading && !latest && (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <RefreshCw className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No weekly review yet.</p>
            <p className="text-xs text-muted-foreground/70 mt-1">Click "Run New Review" to generate your first report.</p>
          </div>
        )}

        {!runMutation.isPending && latest && (
          <ReviewContent review={runMutation.data ?? latest} />
        )}
      </div>
    </div>
  );
}
