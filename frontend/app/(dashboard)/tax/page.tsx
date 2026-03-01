"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Loader2, DollarSign, TrendingDown, AlertCircle, CheckCircle, Mail, ChevronDown, ChevronUp } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { taxApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface Deduction {
  category: string;
  description: string;
  estimated_amount: number;
  deduction_type: string;
  confidence: "likely" | "possible" | "unlikely";
  notes: string;
}

interface TaxResult {
  response: string;
  structured_data: {
    deductions: Deduction[];
    tax_saving_strategies: string[];
    estimated_total_deductions: number;
    estimated_tax_savings: number;
    assumed_tax_rate: number;
    disclaimer: string;
    tax_year: number;
    data_summary: {
      total_income: number;
      total_expenses: number;
      spending_by_category: Record<string, number>;
    };
  };
}

const CONFIDENCE_CONFIG = {
  likely: { label: "Likely", color: "text-green-400", bg: "bg-green-500/10 border-green-500/20" },
  possible: { label: "Possible", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" },
  unlikely: { label: "Unlikely", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
};

function DeductionCard({ d }: { d: Deduction }) {
  const [open, setOpen] = useState(false);
  const cfg = CONFIDENCE_CONFIG[d.confidence] || CONFIDENCE_CONFIG.possible;
  return (
    <div className={`border rounded-xl p-4 ${cfg.bg}`}>
      <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={() => setOpen((v) => !v)}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold">{d.category}</h4>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.color}`}>
              {cfg.label}
            </span>
            <span className="text-[10px] text-muted-foreground capitalize">{d.deduction_type.replace("_", " ")}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{d.description}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-sm font-bold text-green-400">{formatCurrency(d.estimated_amount)}</p>
          <p className="text-[10px] text-muted-foreground">deductible</p>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" /> : <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />}
      </div>
      {open && d.notes && (
        <p className="text-xs text-muted-foreground mt-3 pt-3 border-t border-border/50">{d.notes}</p>
      )}
    </div>
  );
}

export default function TaxPage() {
  const currentYear = new Date().getFullYear();
  const defaultYear = new Date().getMonth() < 3 ? currentYear - 1 : currentYear;
  const [taxYear, setTaxYear] = useState(defaultYear);
  const [emailSent, setEmailSent] = useState(false);

  const { data: result, isLoading, refetch } = useQuery<TaxResult>({
    queryKey: ["tax-analysis", taxYear],
    queryFn: () => taxApi.analyze(taxYear).then((r) => r.data),
  });

  const emailMutation = useMutation({
    mutationFn: () => taxApi.emailReport(taxYear).then((r) => r.data),
    onSuccess: () => { setEmailSent(true); setTimeout(() => setEmailSent(false), 4000); },
  });

  const sd = result?.structured_data;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Tax Savings"
        subtitle="AI-detected deductions from your spending"
        actions={
          <div className="flex items-center gap-2">
            <select
              value={taxYear}
              onChange={(e) => setTaxYear(Number(e.target.value))}
              className="text-xs bg-muted border border-border rounded-lg px-2 py-1.5 focus:outline-none"
            >
              {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={() => emailMutation.mutate()}
              disabled={emailMutation.isPending || !result}
              className="flex items-center gap-1.5 text-xs bg-green-500/10 text-green-400 border border-green-500/20 px-3 py-1.5 rounded-lg hover:bg-green-500/20 disabled:opacity-50 transition-colors"
            >
              {emailMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
              Email Report
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-5">
        {emailSent && (
          <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3 text-sm text-green-400">
            <CheckCircle className="h-4 w-4" />
            Tax report emailed to your account.
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col items-center justify-center h-48 space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm font-medium">Analyzing your {taxYear} transactions...</p>
            <p className="text-xs text-muted-foreground">Finding potential deductions and tax savings</p>
          </div>
        )}

        {!isLoading && sd && (
          <>
            {/* Summary stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-card border border-border rounded-xl p-3">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <DollarSign className="h-3 w-3" /> Tax Year
                </p>
                <p className="text-lg font-bold mt-1">{sd.tax_year}</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-3">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" /> Est. Deductions
                </p>
                <p className="text-lg font-bold text-blue-400 mt-1">{formatCurrency(sd.estimated_total_deductions)}</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-3">
                <p className="text-xs text-muted-foreground">Est. Tax Savings</p>
                <p className="text-lg font-bold text-green-400 mt-1">{formatCurrency(sd.estimated_tax_savings)}</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-3">
                <p className="text-xs text-muted-foreground">Assumed Rate</p>
                <p className="text-lg font-bold mt-1">{sd.assumed_tax_rate}%</p>
              </div>
            </div>

            {/* Deductions list */}
            {sd.deductions.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Identified Deductions ({sd.deductions.length})</h3>
                {sd.deductions.map((d, i) => <DeductionCard key={i} d={d} />)}
              </div>
            )}

            {/* Strategies */}
            {sd.tax_saving_strategies.length > 0 && (
              <div className="bg-card border border-border rounded-xl p-4">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-400" /> Tax Saving Strategies
                </h3>
                <ul className="space-y-2">
                  {sd.tax_saving_strategies.map((s, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                      <span className="text-green-400 mt-0.5">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI Narrative */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold mb-3">AI Analysis</h3>
              <div className="space-y-2">
                {result.response.split("\n").map((line, i) => {
                  if (line.startsWith("## ")) return <h4 key={i} className="text-sm font-bold mt-4 mb-1">{line.replace("## ", "")}</h4>;
                  if (line.startsWith("**") && line.endsWith("**")) return <p key={i} className="text-sm font-semibold mt-2">{line.replace(/\*\*/g, "")}</p>;
                  if (line.startsWith("- ") || line.startsWith("• ")) return <p key={i} className="text-xs text-muted-foreground pl-3">• {line.slice(2)}</p>;
                  if (line.trim() === "") return <div key={i} className="h-1.5" />;
                  return <p key={i} className="text-xs text-muted-foreground leading-relaxed">{line}</p>;
                })}
              </div>
            </div>

            {/* Disclaimer */}
            <div className="flex items-start gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3">
              <AlertCircle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
              <p className="text-xs text-muted-foreground">{sd.disclaimer}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
