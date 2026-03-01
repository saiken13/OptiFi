"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { PiggyBank, Plus, Trash2 } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { BudgetHealthChart } from "@/components/dashboard/BudgetHealthChart";
import { budgetsApi } from "@/lib/api";
import type { Budget } from "@/types";
import { formatCurrency, CATEGORIES, CATEGORY_COLORS } from "@/lib/utils";

const schema = z.object({
  category: z.string().min(1),
  monthly_limit: z.coerce.number().positive(),
  month: z.coerce.number().min(1).max(12),
  year: z.coerce.number().min(2020).max(2099),
});

type FormData = z.infer<typeof schema>;

const now = new Date();

export default function BudgetsPage() {
  const [showForm, setShowForm] = useState(false);
  const qc = useQueryClient();

  const { data: budgets = [], isLoading } = useQuery<Budget[]>({
    queryKey: ["budgets"],
    queryFn: () => budgetsApi.list().then((r) => r.data),
  });

  const { register, handleSubmit, reset } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { month: now.getMonth() + 1, year: now.getFullYear() },
  });

  const createBudget = useMutation({
    mutationFn: (data: FormData) => budgetsApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["budgets"] }); reset(); setShowForm(false); },
  });

  const deleteBudget = useMutation({
    mutationFn: (id: string) => budgetsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budgets"] }),
  });

  const budgetHealth = budgets.map((b) => {
    const pct = b.monthly_limit > 0 ? (b.spent_this_month / b.monthly_limit) * 100 : 0;
    return {
      category: b.category,
      limit: b.monthly_limit,
      spent: b.spent_this_month,
      percent_used: pct,
      status: (pct > 100 ? "over" : pct > 80 ? "warning" : "ok") as "ok" | "warning" | "over",
    };
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Budgets"
        subtitle={`${now.toLocaleString("default", { month: "long" })} ${now.getFullYear()}`}
        actions={
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:opacity-90">
            <Plus className="h-3 w-3" /> Add Budget
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {budgets.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">Spending vs Limits</h3>
            <BudgetHealthChart data={budgetHealth} />
          </div>
        )}

        {showForm && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">New Budget</h3>
            <form onSubmit={handleSubmit((d) => createBudget.mutate(d))} className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Category</label>
                <select {...register("category")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none">
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Monthly Limit ($)</label>
                <input type="number" {...register("monthly_limit")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="500" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Month</label>
                <input type="number" {...register("month")} min={1} max={12} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Year</label>
                <input type="number" {...register("year")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div className="col-span-2 flex gap-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-border rounded-lg py-1.5 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createBudget.isPending} className="flex-1 bg-primary text-primary-foreground rounded-lg py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-50">
                  {createBudget.isPending ? "Saving..." : "Save Budget"}
                </button>
              </div>
            </form>
          </div>
        )}

        {isLoading ? (
          <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
        ) : budgets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <PiggyBank className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No budgets set</p>
            <button onClick={() => setShowForm(true)} className="mt-3 text-xs text-primary hover:underline">Set your first budget</button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {budgets.map((b) => {
              const pct = b.monthly_limit > 0 ? (b.spent_this_month / b.monthly_limit) * 100 : 0;
              const color = CATEGORY_COLORS[b.category] || "#94a3b8";
              const status = pct > 100 ? "over" : pct > 80 ? "warning" : "ok";
              return (
                <div key={b.id} className="bg-card border border-border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-sm font-semibold capitalize">{b.category}</span>
                    </div>
                    <button onClick={() => deleteBudget.mutate(b.id)} className="p-1 hover:bg-destructive/10 hover:text-destructive rounded">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-lg font-bold">{formatCurrency(b.spent_this_month)}</span>
                    <span className="text-xs text-muted-foreground">of {formatCurrency(b.monthly_limit)}</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, pct)}%`,
                        backgroundColor: status === "over" ? "#ef4444" : status === "warning" ? "#eab308" : "#22c55e",
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span className={status === "over" ? "text-red-400 font-medium" : status === "warning" ? "text-yellow-400 font-medium" : "text-green-400 font-medium"}>
                      {status === "over" ? "Over budget!" : status === "warning" ? "Near limit" : "On track"}
                    </span>
                    <span>{formatCurrency(Math.max(0, b.monthly_limit - b.spent_this_month))} left</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
