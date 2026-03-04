"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Loader2, Mic, MicOff } from "lucide-react";
import { chatApi } from "@/lib/api";
import type { ChatMessage } from "@/types";
import { MessageBubble } from "./MessageBubble";

const SUGGESTED_PROMPTS = [
  "How is my budget looking this month?",
  "Am I on track with my savings goals?",
  "What's the best strategy to pay off my loans?",
  "Where should I buy a new laptop and which card to use?",
  "Give me a weekly financial review",
];

type SpeechRecognitionResultLike = {
  transcript: string;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>>;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const qc = useQueryClient();

  const { data: history = [], isLoading: historyLoading } = useQuery<ChatMessage[]>({
    queryKey: ["chat-history"],
    queryFn: () => chatApi.history(50).then((r) => r.data),
  });

  const sendMessage = useMutation({
    mutationFn: (message: string) => chatApi.send(message).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-history"] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["goals"] });
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["txn-summary"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessage[]>([]);

  const allMessages = [...history, ...optimisticMessages];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [allMessages]);

  const handleSend = async (text?: string) => {
    const message = text || input.trim();
    if (!message || sendMessage.isPending) return;

    setInput("");

    const optimistic: ChatMessage = {
      id: `optimistic-${Date.now()}`,
      role: "user",
      content: message,
      agent_type: null,
      structured_data: null,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages([optimistic]);

    try {
      await sendMessage.mutateAsync(message);
    } finally {
      setOptimisticMessages([]);
    }
  };

  const toggleMic = () => {
    const w = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? prev + " " + transcript : transcript));
    };

    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {historyLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : allMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Ask OptiFi anything</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Your AI financial advisor is ready. Ask about budgets, goals, loans, or where to make your next purchase.
              </p>
            </div>
            <div className="grid gap-2 w-full max-w-md">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSend(prompt)}
                  className="text-left text-sm px-4 py-2.5 rounded-lg bg-card border border-border hover:bg-accent hover:border-primary/30 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          allMessages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {sendMessage.isPending && (
          <div className="flex gap-3">
            <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0" />
            <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center">
                <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2 items-end bg-card border border-border rounded-xl px-4 py-2.5">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your finances..."
            rows={1}
            className="flex-1 bg-transparent text-sm resize-none focus:outline-none max-h-28 leading-relaxed"
            style={{ minHeight: "24px" }}
          />
          <button
            onClick={toggleMic}
            disabled={sendMessage.isPending}
            title={isListening ? "Stop recording" : "Voice input"}
            className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 transition-all disabled:opacity-40 ${
              isListening
                ? "bg-red-500 text-white animate-pulse"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {isListening ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || sendMessage.isPending}
            className="h-7 w-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center disabled:opacity-40 hover:opacity-90 transition-opacity shrink-0"
          >
            {sendMessage.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground/50 text-center mt-2">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
