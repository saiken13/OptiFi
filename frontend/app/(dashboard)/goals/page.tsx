"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Target, Plus, Trash2, TrendingUp } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { goalsApi } from "@/lib/api";
import type { Goal } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { calculate_months_to_goal } from "@/lib/goalUtils";

const schema = z.object({
  name: z.string().min(1),
  target_amount: z.coerce.number().positive(),
  current_amount: z.coerce.number().min(0).default(0),
  monthly_contribution: z.coerce.number().min(0).default(0),
  target_date: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function GoalsPage() {
  const [showForm, setShowForm] = useState(false);
  const qc = useQueryClient();

  const { data: goals = [], isLoading } = useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => goalsApi.list().then((r) => r.data),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const createGoal = useMutation({
    mutationFn: (data: FormData) => goalsApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["goals"] }); reset(); setShowForm(false); },
  });

  const deleteGoal = useMutation({
    mutationFn: (id: string) => goalsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Savings Goals"
        subtitle="Track your financial milestones"
        actions={
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:opacity-90"
          >
            <Plus className="h-3 w-3" /> Add Goal
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {showForm && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">New Goal</h3>
            <form onSubmit={handleSubmit((d) => createGoal.mutate(d))} className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-xs text-muted-foreground mb-1">Goal Name</label>
                <input {...register("name")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Emergency fund, Vacation, etc." />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Target Amount</label>
                <input type="number" {...register("target_amount")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="10000" />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Current Amount</label>
                <input type="number" {...register("current_amount")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="0" />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Monthly Contribution</label>
                <input type="number" {...register("monthly_contribution")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="500" />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Target Date (optional)</label>
                <input type="date" {...register("target_date")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div className="col-span-2 flex gap-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-border rounded-lg py-1.5 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createGoal.isPending} className="flex-1 bg-primary text-primary-foreground rounded-lg py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-50">
                  {createGoal.isPending ? "Saving..." : "Save Goal"}
                </button>
              </div>
            </form>
          </div>
        )}

        {isLoading ? (
          <div className="text-center text-sm text-muted-foreground py-8">Loading goals...</div>
        ) : goals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <Target className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No goals yet</p>
            <button onClick={() => setShowForm(true)} className="mt-3 text-xs text-primary hover:underline">Add your first goal</button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {goals.map((goal) => {
              const pct = Math.min(100, (goal.current_amount / goal.target_amount) * 100);
              const monthsLeft = calculate_months_to_goal(goal.target_amount, goal.current_amount, goal.monthly_contribution);
              const colors = ["#3b82f6", "#22c55e", "#f97316", "#8b5cf6", "#ec4899"];
              const color = colors[goals.indexOf(goal) % colors.length];

              return (
                <div key={goal.id} className="bg-card border border-border rounded-xl p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Target className="h-4 w-4 shrink-0" style={{ color }} />
                      <h4 className="text-sm font-semibold truncate">{goal.name}</h4>
                    </div>
                    <button onClick={() => deleteGoal.mutate(goal.id)} className="p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-colors ml-2 shrink-0">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-xl font-bold">{formatCurrency(goal.current_amount)}</span>
                    <span className="text-xs text-muted-foreground">of {formatCurrency(goal.target_amount)}</span>
                  </div>

                  <div className="h-1.5 bg-muted rounded-full mb-3 overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{pct.toFixed(0)}% complete</span>
                    {monthsLeft !== null ? (
                      <span className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        ~{Math.ceil(monthsLeft)}mo left
                      </span>
                    ) : (
                      <span>No contribution set</span>
                    )}
                  </div>
                  {goal.monthly_contribution > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      +{formatCurrency(goal.monthly_contribution)}/mo
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
