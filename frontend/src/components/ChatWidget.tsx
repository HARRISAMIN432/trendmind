"use client";

import Link from "next/link";
import { FormEvent, useRef, useState } from "react";
import { Loader2, MessageSquare, Send, Sparkles } from "lucide-react";
import { sendChatMessage } from "@/lib/api";
import type { ChatCitation, ChatTurn } from "@/lib/types";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface ChatWidgetProps {
  category?: string | null;
  compact?: boolean;
}

export function ChatWidget({ category, compact = false }: ChatWidgetProps) {
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userTurn: ChatTurn = { role: "user", content: question };
    const nextHistory = [...messages, userTurn];
    setMessages(nextHistory);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage(
        question,
        messages,
        category ?? undefined,
      );
      setMessages([
        ...nextHistory,
        { role: "assistant", content: response.answer },
      ]);
      setCitations(response.citations);
    } catch {
      setError("Failed to get a response. Check that the backend is running.");
    } finally {
      setLoading(false);
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
    }
  }

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)]",
        compact ? "h-[420px]" : "h-[560px]",
      )}
    >
      <div className="flex items-center gap-2 border-b border-[var(--border)] px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg bg-[var(--accent)]">
          <Image
            src="/logo.png"
            alt="DigestAI"
            width={32}
            height={32}
            className="h-full w-full object-cover"
          />
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            Ask DigestAI
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            Chat with your news corpus
          </p>
        </div>
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquare className="mb-3 h-8 w-8 text-[var(--text-muted)]" />
            <p className="text-sm text-[var(--text-secondary)]">
              Ask a question about recent AI news
            </p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Answers are grounded in retrieved articles with citations
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "max-w-[90%] rounded-lg px-3 py-2 text-sm leading-relaxed",
              msg.role === "user"
                ? "ml-auto bg-[var(--accent)] text-white"
                : "bg-[var(--bg-tertiary)] text-[var(--text-primary)]",
            )}
          >
            {msg.content}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Searching and synthesizing...
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>

      {citations.length > 0 && (
        <div className="border-t border-[var(--border)] px-4 py-3">
          <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">
            Sources
          </p>
          <div className="flex flex-wrap gap-2">
            {citations.slice(0, 4).map(({ article, relevance_score }) => (
              <Link
                key={article.id}
                href={`/article/${article.id}`}
                className="rounded-md border border-[var(--border)] px-2 py-1 text-xs text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
              >
                {article.title.slice(0, 40)}
                {article.title.length > 40 ? "…" : ""}{" "}
                <span className="text-[var(--text-muted)]">
                  ({Math.round(relevance_score * 100)}%)
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="flex gap-2 border-t border-[var(--border)] p-4"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What happened in AI this week?"
          disabled={loading}
          className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--accent)] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="inline-flex items-center justify-center rounded-lg bg-[var(--accent)] px-3 py-2 text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
