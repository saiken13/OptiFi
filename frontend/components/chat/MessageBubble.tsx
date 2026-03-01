"use client";

import ReactMarkdown from "react-markdown";
import { cn, AGENT_LABELS } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { formatDate } from "@/lib/utils";
import { DollarSign } from "lucide-react";

interface Props {
  message: ChatMessage;
}

const AGENT_BADGE_COLORS: Record<string, string> = {
  budget: "bg-orange-500/10 text-orange-400",
  goal: "bg-blue-500/10 text-blue-400",
  loan: "bg-red-500/10 text-red-400",
  purchase_optimize: "bg-green-500/10 text-green-400",
  weekly_review: "bg-purple-500/10 text-purple-400",
  card_import: "bg-yellow-500/10 text-yellow-400",
  general: "bg-muted text-muted-foreground",
};

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
          <p className="text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 max-w-[85%]">
      <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
        <DollarSign className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-xs font-semibold text-foreground">OptiFi</span>
          {message.agent_type && (
            <span
              className={cn(
                "text-[10px] font-medium px-1.5 py-0.5 rounded-full",
                AGENT_BADGE_COLORS[message.agent_type] || "bg-muted text-muted-foreground"
              )}
            >
              {AGENT_LABELS[message.agent_type] || message.agent_type}
            </span>
          )}
          <span className="text-[10px] text-muted-foreground/60 ml-auto">
            {formatDate(message.created_at)}
          </span>
        </div>
        <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 prose-chat">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
