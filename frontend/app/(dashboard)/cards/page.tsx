"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus, Trash2, Sparkles, ChevronDown, ChevronRight } from "lucide-react";
import { Header } from "@/components/shared/Header";
import { CardImportWizard } from "@/components/cards/CardImportWizard";
import { cardsApi } from "@/lib/api";
import type { Card } from "@/types";
import { formatCurrency } from "@/lib/utils";

export default function CardsPage() {
  const [showImport, setShowImport] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: cards = [], isLoading } = useQuery<Card[]>({
    queryKey: ["cards"],
    queryFn: () => cardsApi.list().then((r) => r.data),
  });

  const deleteCard = useMutation({
    mutationFn: (id: string) => cardsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cards"] }),
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Credit Cards"
        subtitle="Manage your cards and reward rules"
        actions={
          <button
            onClick={() => setShowImport(!showImport)}
            className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
          >
            <Sparkles className="h-3 w-3" />
            AI Import Card
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Import Wizard */}
        {showImport && (
          <div className="bg-card border border-primary/20 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">AI Card Import</h3>
              <span className="text-xs text-muted-foreground ml-auto">
                AI extracts reward rules from the issuer&apos;s website
              </span>
            </div>
            <CardImportWizard onSuccess={() => setShowImport(false)} />
          </div>
        )}

        {/* Cards List */}
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
            Loading cards...
          </div>
        ) : cards.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <CreditCard className="h-10 w-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No cards added yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Use AI Import to automatically extract reward rules from your card issuer
            </p>
            <button
              onClick={() => setShowImport(true)}
              className="mt-4 flex items-center gap-1.5 text-xs bg-primary/10 text-primary px-3 py-1.5 rounded-lg hover:bg-primary/20"
            >
              <Sparkles className="h-3 w-3" />
              Import First Card
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {cards.map((card) => (
              <div key={card.id} className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-3 p-4">
                  <div className="h-9 w-14 bg-gradient-to-br from-primary/20 to-primary/5 rounded-lg flex items-center justify-center">
                    <CreditCard className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">{card.name}</p>
                      {card.network && (
                        <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                          {card.network.toUpperCase()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{card.issuer}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {card.reward_rules.length} rules
                    </span>
                    {card.annual_fee > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {formatCurrency(card.annual_fee)}/yr
                      </span>
                    )}
                    <button
                      onClick={() =>
                        setExpandedCard(expandedCard === card.id ? null : card.id)
                      }
                      className="p-1 hover:bg-accent rounded"
                    >
                      {expandedCard === card.id ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                    </button>
                    <button
                      onClick={() => deleteCard.mutate(card.id)}
                      className="p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {expandedCard === card.id && card.reward_rules.length > 0 && (
                  <div className="border-t border-border">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-muted/30">
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Category</th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Type</th>
                          <th className="text-right px-4 py-2 font-medium text-muted-foreground">Rate</th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Cap</th>
                        </tr>
                      </thead>
                      <tbody>
                        {card.reward_rules.map((rule) => (
                          <tr key={rule.id} className="border-t border-border/50">
                            <td className="px-4 py-2 capitalize font-medium">{rule.category}</td>
                            <td className="px-4 py-2 capitalize text-muted-foreground">{rule.rule_type}</td>
                            <td className="px-4 py-2 text-right text-green-400 font-semibold">
                              {(rule.reward_rate * 100).toFixed(1)}%
                            </td>
                            <td className="px-4 py-2 text-muted-foreground">
                              {rule.cap_amount
                                ? `${formatCurrency(rule.cap_amount)}/${rule.cap_period || "yr"}`
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
