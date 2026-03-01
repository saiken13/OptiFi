"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { TrendingUp, Plus, Trash2 } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { LoanPayoffChart } from "@/components/dashboard/LoanPayoffChart";
import { loansApi } from "@/lib/api";
import type { Loan } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { loan_amortization } from "@/lib/loanUtils";

const schema = z.object({
  name: z.string().min(1),
  loan_type: z.string().default("personal"),
  principal: z.coerce.number().positive(),
  current_balance: z.coerce.number().positive(),
  interest_rate: z.coerce.number().positive(),
  monthly_payment: z.coerce.number().positive(),
  extra_payment: z.coerce.number().min(0).default(0),
});

type FormData = z.infer<typeof schema>;

export default function LoansPage() {
  const [showForm, setShowForm] = useState(false);
  const qc = useQueryClient();

  const { data: loans = [], isLoading } = useQuery<Loan[]>({
    queryKey: ["loans"],
    queryFn: () => loansApi.list().then((r) => r.data),
  });

  const { register, handleSubmit, reset } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const createLoan = useMutation({
    mutationFn: (data: FormData) => loansApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["loans"] }); reset(); setShowForm(false); },
  });

  const deleteLoan = useMutation({
    mutationFn: (id: string) => loansApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["loans"] }),
  });

  const totalDebt = loans.reduce((s, l) => s + l.current_balance, 0);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Loans & Debt"
        subtitle="Track and optimize your debt payoff"
        actions={
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:opacity-90">
            <Plus className="h-3 w-3" /> Add Loan
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {loans.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-xs text-muted-foreground">Total Debt</p>
              <p className="text-xl font-bold text-red-400 mt-1">{formatCurrency(totalDebt)}</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-xs text-muted-foreground">Loans</p>
              <p className="text-xl font-bold mt-1">{loans.length}</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-xs text-muted-foreground">Monthly Payments</p>
              <p className="text-xl font-bold mt-1">
                {formatCurrency(loans.reduce((s, l) => s + l.monthly_payment + l.extra_payment, 0))}
              </p>
            </div>
          </div>
        )}

        {loans.length > 0 && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">Payoff Curve</h3>
            <LoanPayoffChart loans={loans} />
          </div>
        )}

        {showForm && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">Add Loan</h3>
            <form onSubmit={handleSubmit((d) => createLoan.mutate(d))} className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="text-xs text-muted-foreground block mb-1">Loan Name</label>
                <input {...register("name")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Student Loan, Car Loan, etc." />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Type</label>
                <select {...register("loan_type")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none">
                  {["personal", "student", "auto", "mortgage", "credit_card"].map((t) => (
                    <option key={t} value={t}>{t.replace("_", " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Original Principal ($)</label>
                <input type="number" {...register("principal")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="25000" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Current Balance ($)</label>
                <input type="number" {...register("current_balance")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="18000" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Annual Interest Rate (%)</label>
                <input type="number" step="0.01" {...register("interest_rate")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="6.5" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Monthly Payment ($)</label>
                <input type="number" {...register("monthly_payment")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="350" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Extra Payment/mo ($)</label>
                <input type="number" {...register("extra_payment")} className="w-full px-3 py-1.5 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="0" />
              </div>
              <div className="col-span-2 flex gap-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-border rounded-lg py-1.5 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createLoan.isPending} className="flex-1 bg-primary text-primary-foreground rounded-lg py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-50">
                  {createLoan.isPending ? "Saving..." : "Save Loan"}
                </button>
              </div>
            </form>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground text-center py-8">Loading...</p>
        ) : loans.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <TrendingUp className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No loans tracked</p>
            <button onClick={() => setShowForm(true)} className="mt-3 text-xs text-primary hover:underline">Add your first loan</button>
          </div>
        ) : (
          <div className="space-y-3">
            {loans.map((loan) => {
              const schedule = loan_amortization(loan.current_balance, loan.interest_rate, loan.monthly_payment, loan.extra_payment);
              const totalInterest = schedule.reduce((s, m) => s + m.interest, 0);
              return (
                <div key={loan.id} className="bg-card border border-border rounded-xl p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold">{loan.name}</h4>
                      <p className="text-xs text-muted-foreground capitalize mt-0.5">{loan.loan_type.replace("_", " ")}</p>
                    </div>
                    <button onClick={() => deleteLoan.mutate(loan.id)} className="p-1 hover:bg-destructive/10 hover:text-destructive rounded">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="grid grid-cols-4 gap-3 mt-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Balance</p>
                      <p className="text-sm font-semibold text-red-400">{formatCurrency(loan.current_balance)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Rate</p>
                      <p className="text-sm font-semibold">{loan.interest_rate}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Monthly</p>
                      <p className="text-sm font-semibold">{formatCurrency(loan.monthly_payment + loan.extra_payment)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Payoff</p>
                      <p className="text-sm font-semibold">{schedule.length}mo</p>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Total interest: {formatCurrency(totalInterest)}
                    {loan.extra_payment > 0 && (
                      <span className="ml-2 text-green-400">
                        +{formatCurrency(loan.extra_payment)}/mo extra
                      </span>
                    )}
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
