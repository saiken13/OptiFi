"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ShoppingCart, Search, Trophy, ArrowRight, ExternalLink, CreditCard, Loader2, Tag } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { purchaseApi } from "@/lib/api";
import type { PurchaseOptimizeResult, OptimizedOption, CardOption } from "@/types";
import { formatCurrency } from "@/lib/utils";

function OptionCard({
  option,
  isBest = false,
}: {
  option: OptimizedOption;
  isBest?: boolean;
}) {
  return (
    <div
      className={`bg-card border rounded-xl p-4 ${
        isBest ? "border-green-500/50 ring-1 ring-green-500/20" : "border-border"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            {isBest && (
              <span className="flex items-center gap-1 text-[10px] font-semibold bg-green-500/10 text-green-500 px-2 py-0.5 rounded-full">
                <Trophy className="h-2.5 w-2.5" /> Best Deal
              </span>
            )}
            <span className="text-xs text-muted-foreground">#{option.rank}</span>
          </div>
          <h4 className="text-base font-semibold mt-1">{option.merchant}</h4>
        </div>
        <div className="text-right">
          <p className="text-xl font-bold text-green-400">{formatCurrency(option.net_cost)}</p>
          <p className="text-xs text-muted-foreground">net cost</p>
        </div>
      </div>

      <div className="space-y-1.5 mb-3">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Price</span>
          <span>{formatCurrency(option.price)}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Shipping</span>
          <div className="flex items-center gap-1">
            {option.shipping_after_membership < option.shipping && (
              <span className="line-through text-muted-foreground/50">
                {formatCurrency(option.shipping)}
              </span>
            )}
            <span className={option.shipping_after_membership === 0 ? "text-green-400" : ""}>
              {option.shipping_after_membership === 0
                ? "FREE"
                : formatCurrency(option.shipping_after_membership)}
            </span>
          </div>
        </div>
        {option.membership_savings > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground flex items-center gap-1">
              <Tag className="h-3 w-3" />
              {option.membership_name} savings
            </span>
            <span className="text-green-400">-{formatCurrency(option.membership_savings)}</span>
          </div>
        )}
        {option.best_card_name && (
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground flex items-center gap-1">
              <CreditCard className="h-3 w-3" />
              {option.best_card_name}
            </span>
            <span className="text-blue-400">
              -{formatCurrency(option.cashback_amount)} ({(option.cashback_rate * 100).toFixed(1)}%)
            </span>
          </div>
        )}
        <div className="flex justify-between text-xs font-semibold border-t border-border pt-1.5 mt-1">
          <span>Total savings</span>
          <span className="text-green-400">{formatCurrency(option.total_savings)}</span>
        </div>
      </div>

      {option.card_options && option.card_options.length > 0 && (
        <div className="mb-3 border border-border rounded-lg overflow-hidden">
          <div className="px-2 py-1 bg-muted/50 flex items-center gap-1">
            <CreditCard className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Card Comparison</span>
          </div>
          <div className="divide-y divide-border/50">
            {option.card_options.map((card: CardOption) => (
              <div key={card.card_name} className="flex items-center justify-between px-2 py-1">
                <span className="text-xs">{card.card_name}</span>
                <span className={`text-xs font-medium ${card.cashback_amount > 0 ? "text-blue-400" : "text-muted-foreground"}`}>
                  {card.cashback_amount > 0
                    ? `-${formatCurrency(card.cashback_amount)} (${(card.cashback_rate * 100).toFixed(1)}%)`
                    : "No reward"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <a
        href={option.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-1.5 w-full bg-accent hover:bg-accent/80 text-foreground rounded-lg py-1.5 text-xs font-medium transition-colors"
      >
        View on {option.merchant}
        <ExternalLink className="h-3 w-3" />
      </a>
    </div>
  );
}

export default function PurchasePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<PurchaseOptimizeResult | null>(null);

  const optimizeMutation = useMutation({
    mutationFn: (q: string) => purchaseApi.optimize(q).then((r) => r.data),
    onSuccess: (data) => setResult(data),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    optimizeMutation.mutate(query.trim());
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Purchase Optimizer"
        subtitle="Find the best price + credit card combination"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Search Form */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold mb-3">What do you want to buy?</h3>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 flex items-center gap-2 bg-input border border-border rounded-lg px-3 py-2">
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. Sony WH-1000XM5 headphones, MacBook Air M3..."
                className="flex-1 bg-transparent text-sm focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={!query.trim() || optimizeMutation.isPending}
              className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {optimizeMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {optimizeMutation.isPending ? "Optimizing..." : "Optimize"}
            </button>
          </form>
          <p className="text-xs text-muted-foreground mt-2">
            We&apos;ll search multiple merchants, apply your membership benefits, and find the best card to maximize savings.
          </p>
        </div>

        {/* Results */}
        {optimizeMutation.isPending && (
          <div className="flex flex-col items-center justify-center h-48 space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <div className="text-center">
              <p className="text-sm font-medium">Searching merchants...</p>
              <p className="text-xs text-muted-foreground mt-1">
                Comparing prices, memberships, and card rewards
              </p>
            </div>
          </div>
        )}

        {result && !optimizeMutation.isPending && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                Results for &ldquo;{result.query}&rdquo;
              </h3>
              <span className="text-xs text-muted-foreground">
                {result.all_options.length} options found
              </span>
            </div>

            {/* Best option */}
            {result.best_option && (
              <OptionCard option={result.best_option} isBest />
            )}

            {/* Alternatives */}
            {result.alternatives.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                  Alternatives
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {result.alternatives.map((opt) => (
                    <OptionCard key={opt.rank} option={opt} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!result && !optimizeMutation.isPending && (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <ShoppingCart className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">
              Enter a product to find the best deal
            </p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Works best when you have cards and memberships set up
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
