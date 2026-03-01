"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cardsApi } from "@/lib/api";
import { Search, FileText, CheckCircle, ExternalLink, Loader2, AlertCircle } from "lucide-react";

type Step = "search" | "select" | "extract" | "confirm";

interface SearchForm {
  card_name: string;
  issuer: string;
}

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

interface RewardRule {
  rule_type: string;
  category: string;
  reward_rate: number;
  cap_amount: number | null;
  cap_period: string | null;
  merchant_match: string | null;
  activation_required: boolean;
  evidence: string | null;
  source_url: string | null;
}

interface Props {
  onSuccess: () => void;
}

export function CardImportWizard({ onSuccess }: Props) {
  const [step, setStep] = useState<Step>("search");
  const [jobId, setJobId] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [extractedRules, setExtractedRules] = useState<RewardRule[]>([]);
  const [editableRules, setEditableRules] = useState<RewardRule[]>([]);
  const [cardInfo, setCardInfo] = useState({ card_name: "", issuer: "" });
  const [selectedUrl, setSelectedUrl] = useState("");
  const qc = useQueryClient();

  const searchMutation = useMutation({
    mutationFn: ({ card_name, issuer }: SearchForm) =>
      cardsApi.importSearch(card_name, issuer).then((r) => r.data),
    onSuccess: (data) => {
      setJobId(data.job_id);
      setSearchResults(data.results);
      setStep("select");
    },
  });

  const extractMutation = useMutation({
    mutationFn: ({ job_id, url }: { job_id: string; url: string }) =>
      cardsApi.importExtract(job_id, url).then((r) => r.data),
    onSuccess: (data) => {
      setExtractedRules(data.rules);
      setEditableRules(JSON.parse(JSON.stringify(data.rules)));
      setStep("confirm");
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () =>
      cardsApi.importConfirm({
        job_id: jobId,
        card_name: cardInfo.card_name,
        issuer: cardInfo.issuer,
        rules: editableRules,
      }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cards"] });
      onSuccess();
    },
  });

  const { register, handleSubmit, formState: { errors } } = useForm<SearchForm>();

  const onSearch = (data: SearchForm) => {
    setCardInfo(data);
    searchMutation.mutate(data);
  };

  const handleSelectUrl = (url: string) => {
    setSelectedUrl(url);
    setStep("extract");
    extractMutation.mutate({ job_id: jobId, url });
  };

  const updateRule = (index: number, field: keyof RewardRule, value: unknown) => {
    setEditableRules((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const removeRule = (index: number) => {
    setEditableRules((prev) => prev.filter((_, i) => i !== index));
  };

  const STEPS = [
    { id: "search", label: "Search", icon: Search },
    { id: "select", label: "Select Page", icon: FileText },
    { id: "confirm", label: "Confirm Rules", icon: CheckCircle },
  ];

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => {
          const stepIdx = STEPS.findIndex((x) => x.id === (step === "extract" ? "select" : step));
          const done = i < stepIdx;
          const active = i === stepIdx;
          return (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold ${
                  done
                    ? "bg-green-500 text-white"
                    : active
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {done ? "✓" : i + 1}
              </div>
              <span className={`text-xs font-medium ${active ? "text-foreground" : "text-muted-foreground"}`}>
                {s.label}
              </span>
              {i < STEPS.length - 1 && <div className="h-px w-6 bg-border" />}
            </div>
          );
        })}
      </div>

      {/* Step: Search */}
      {step === "search" && (
        <form onSubmit={handleSubmit(onSearch)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Card Name</label>
            <input
              {...register("card_name", { required: true })}
              className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. Sapphire Preferred, Freedom Unlimited"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Issuer / Bank</label>
            <input
              {...register("issuer", { required: true })}
              className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. Chase, American Express, Capital One"
            />
          </div>
          <button
            type="submit"
            disabled={searchMutation.isPending}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {searchMutation.isPending ? "Searching..." : "Search Reward Pages"}
          </button>
        </form>
      )}

      {/* Step: Select URL */}
      {step === "select" && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Select the most relevant page for <strong>{cardInfo.card_name}</strong> by{" "}
            <strong>{cardInfo.issuer}</strong>:
          </p>
          {searchResults.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-yellow-500 bg-yellow-500/10 px-3 py-2 rounded-lg">
              <AlertCircle className="h-4 w-4" />
              No results found. Try a different card name or issuer.
            </div>
          ) : (
            searchResults.map((result, i) => (
              <div key={i} className="border border-border rounded-lg p-3 hover:bg-accent transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{result.title}</p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{result.url}</p>
                    {result.snippet && (
                      <p className="text-xs text-muted-foreground/80 mt-1 line-clamp-2">{result.snippet}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1 hover:text-primary"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                    <button
                      onClick={() => handleSelectUrl(result.url)}
                      disabled={extractMutation.isPending}
                      className="text-xs bg-primary text-primary-foreground px-3 py-1 rounded-md hover:opacity-90 disabled:opacity-50"
                    >
                      Extract
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
          {extractMutation.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Fetching page and extracting reward rules...
            </div>
          )}
        </div>
      )}

      {/* Step: Extract loading */}
      {step === "extract" && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Extracting reward rules with AI...</p>
        </div>
      )}

      {/* Step: Confirm */}
      {step === "confirm" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Review and edit the extracted rules before saving.
            </p>
            <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
              {editableRules.length} rules
            </span>
          </div>

          {editableRules.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-yellow-500 bg-yellow-500/10 px-3 py-2 rounded-lg">
              <AlertCircle className="h-4 w-4" />
              No rules were extracted. The page may not have enough reward information.
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {editableRules.map((rule, i) => (
                <div key={i} className="border border-border rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Rule {i + 1}
                    </span>
                    <button
                      onClick={() => removeRule(i)}
                      className="text-xs text-destructive hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-muted-foreground">Category</label>
                      <input
                        value={rule.category}
                        onChange={(e) => updateRule(i, "category", e.target.value)}
                        className="w-full mt-0.5 px-2 py-1 bg-input border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Reward Rate</label>
                      <div className="flex items-center gap-1 mt-0.5">
                        <input
                          type="number"
                          step="0.001"
                          value={rule.reward_rate}
                          onChange={(e) => updateRule(i, "reward_rate", parseFloat(e.target.value))}
                          className="w-full px-2 py-1 bg-input border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                        />
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          = {(rule.reward_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Type</label>
                      <select
                        value={rule.rule_type}
                        onChange={(e) => updateRule(i, "rule_type", e.target.value)}
                        className="w-full mt-0.5 px-2 py-1 bg-input border border-border rounded text-xs focus:outline-none"
                      >
                        <option value="cashback">Cashback</option>
                        <option value="points">Points</option>
                        <option value="miles">Miles</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Activation Required</label>
                      <div className="flex items-center gap-2 mt-1.5">
                        <input
                          type="checkbox"
                          checked={rule.activation_required}
                          onChange={(e) => updateRule(i, "activation_required", e.target.checked)}
                          className="rounded"
                        />
                        <span className="text-xs">Yes</span>
                      </div>
                    </div>
                  </div>
                  {rule.evidence && (
                    <div className="mt-1 p-2 bg-muted/50 rounded text-xs text-muted-foreground italic">
                      &ldquo;{rule.evidence.slice(0, 150)}...&rdquo;
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={() => setStep("select")}
              className="flex-1 border border-border rounded-lg py-2 text-sm hover:bg-accent transition-colors"
            >
              Back
            </button>
            <button
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending || editableRules.length === 0}
              className="flex-1 flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-lg py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {confirmMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              {confirmMutation.isPending ? "Saving..." : "Confirm & Save Card"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
