"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { Receipt, Upload, CheckCircle, Loader2, Plus, X, ChevronLeft, ChevronRight } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { transactionsApi } from "@/lib/api";
import type { Transaction } from "@/types";
import { formatCurrency, CATEGORY_COLORS, CATEGORIES } from "@/lib/utils";

const today = new Date().toISOString().split("T")[0];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

export default function TransactionsPage() {
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [importedCount, setImportedCount] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ date: today, description: "", amount: "", category: "" });
  const now = new Date();
  const [summaryMonth, setSummaryMonth] = useState(now.getMonth() + 1);
  const [summaryYear, setSummaryYear] = useState(now.getFullYear());
  const qc = useQueryClient();

  const { data: transactions = [], isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions"],
    queryFn: () => transactionsApi.list({ limit: 500 }).then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ["txn-summary", summaryMonth, summaryYear],
    queryFn: () => transactionsApi.summary(summaryMonth, summaryYear).then((r) => r.data),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => transactionsApi.upload(file),
    onSuccess: (data) => {
      setImportedCount(data.data.imported);
      setUploadStatus("done");
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["txn-summary"] });
    },
    onError: () => setUploadStatus("error"),
  });

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) {
      setUploadStatus("uploading");
      uploadMutation.mutate(files[0]);
    }
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    maxFiles: 1,
  });

  const createMutation = useMutation({
    mutationFn: (data: object) => transactionsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["txn-summary"] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      setForm({ date: today, description: "", amount: "", category: "" });
      setShowForm(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!form.description || isNaN(amount)) return;
    createMutation.mutate({
      date: form.date,
      description: form.description,
      amount,
      category: form.category || null,
    });
  };

  const prevMonth = () => {
    if (summaryMonth === 1) { setSummaryMonth(12); setSummaryYear((y) => y - 1); }
    else setSummaryMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (summaryMonth === 12) { setSummaryMonth(1); setSummaryYear((y) => y + 1); }
    else setSummaryMonth((m) => m + 1);
  };

  // Filter transaction list to the selected month/year for summary stats.
  // Parse date string directly to avoid UTC→local timezone shift that new Date() causes.
  const filteredTxns = transactions.filter((t) => {
    const parts = (t.date || "").split("-");
    return parseInt(parts[0]) === summaryYear && parseInt(parts[1]) === summaryMonth;
  });

  // For the list display: show filtered if that month has data, else show all sorted by date
  const listTxns = filteredTxns.length > 0 ? filteredTxns : transactions.slice().sort((a, b) => b.date.localeCompare(a.date));
  const showingAll = filteredTxns.length === 0 && transactions.length > 0;

  return (
    <div className="flex flex-col h-full">
      <Header title="Transactions" subtitle="Import and review your spending" />

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          {/* Month navigator */}
          <div className="flex items-center gap-2">
            <button onClick={prevMonth} className="h-7 w-7 rounded-lg bg-muted flex items-center justify-center hover:bg-accent transition-colors">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-medium w-36 text-center">{MONTH_NAMES[summaryMonth - 1]} {summaryYear}</span>
            <button onClick={nextMonth} className="h-7 w-7 rounded-lg bg-muted flex items-center justify-center hover:bg-accent transition-colors">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1.5 text-sm bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 transition-colors"
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "Cancel" : "Add Transaction"}
          </button>
        </div>

        {/* Manual Entry Form */}
        {showForm && (
          <form onSubmit={handleSubmit} className="bg-card border border-border rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold">New Transaction</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Date</label>
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                  className="w-full mt-1 text-sm bg-background border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Amount (negative = expense)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="-42.50"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  className="w-full mt-1 text-sm bg-background border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-muted-foreground">Description</label>
                <input
                  type="text"
                  placeholder="e.g. Grocery run at Trader Joe's"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  className="w-full mt-1 text-sm bg-background border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Category (optional)</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full mt-1 text-sm bg-background border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">— none —</option>
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="w-full flex items-center justify-center gap-1.5 text-sm bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  Save
                </button>
              </div>
            </div>
            {createMutation.isError && (
              <p className="text-xs text-red-400">Failed to save transaction. Please try again.</p>
            )}
          </form>
        )}

        {/* Upload Zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-accent/50"
          }`}
        >
          <input {...getInputProps()} />
          {uploadStatus === "uploading" ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Processing transactions...</p>
            </div>
          ) : uploadStatus === "done" ? (
            <div className="flex flex-col items-center gap-2">
              <CheckCircle className="h-6 w-6 text-green-500" />
              <p className="text-sm font-medium">{importedCount} transactions imported!</p>
              <p className="text-xs text-muted-foreground">Use the month selector above to view different periods</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="text-sm font-medium">Drop your bank CSV here</p>
              <p className="text-xs text-muted-foreground">
                Supports CSV exports from Chase, Bank of America, Mint, and most banks
              </p>
              <span className="text-xs text-primary">Click to select file</span>
            </div>
          )}
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-card border border-border rounded-xl p-3">
              <p className="text-xs text-muted-foreground">Income</p>
              <p className="text-lg font-bold text-green-400">{formatCurrency(summary.total_income)}</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-3">
              <p className="text-xs text-muted-foreground">Expenses</p>
              <p className="text-lg font-bold text-red-400">{formatCurrency(summary.total_expenses)}</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-3">
              <p className="text-xs text-muted-foreground">Net</p>
              <p className={`text-lg font-bold ${summary.net >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatCurrency(summary.net)}
              </p>
            </div>
          </div>
        )}

        {/* Spending by Category */}
        {summary && Object.keys(summary.by_category).length > 0 && (
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3">Spending by Category</h3>
            <div className="space-y-2">
              {Object.entries(summary.by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([cat, amount]) => {
                  const pct = (amount / summary.total_expenses) * 100;
                  const color = CATEGORY_COLORS[cat] || "#94a3b8";
                  return (
                    <div key={cat}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="capitalize">{cat}</span>
                        <span>{formatCurrency(amount)} ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Transaction List */}
        {isLoading ? (
          <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
        ) : transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <Receipt className="h-8 w-8 text-muted-foreground/30 mb-2" />
            <p className="text-sm text-muted-foreground">No transactions yet.</p>
            <p className="text-xs text-muted-foreground mt-1">Import a CSV or add one manually.</p>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                {showingAll
                  ? "All Transactions"
                  : `Transactions — ${MONTH_NAMES[summaryMonth - 1]} ${summaryYear}`}
              </h3>
              <span className="text-xs text-muted-foreground">
                {showingAll
                  ? `${listTxns.length} entries — no data for ${MONTH_NAMES[summaryMonth - 1]} ${summaryYear}`
                  : `${listTxns.length} entries`}
              </span>
            </div>
            <div className="divide-y divide-border/50">
              {listTxns.map((txn) => (
                <div key={txn.id} className="flex items-center gap-3 px-4 py-2.5">
                  <div
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: CATEGORY_COLORS[txn.category || "other"] || "#94a3b8" }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{txn.description}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {txn.date} {txn.category && `• ${txn.category}`}
                    </p>
                  </div>
                  <span className={`text-sm font-semibold shrink-0 ${txn.amount < 0 ? "text-red-400" : "text-green-400"}`}>
                    {txn.amount < 0 ? "-" : "+"}
                    {formatCurrency(Math.abs(txn.amount))}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
