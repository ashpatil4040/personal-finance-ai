import { Send, Sparkles, User } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";

interface Msg {
  role: "user" | "ai";
  text: string;
  tools?: string[];
}

const EXAMPLES = [
  "How much did I spend on dining?",
  "What's my biggest spending category?",
  "How much could I save by cutting dining 30%?",
  "Show my largest transactions this period.",
];

export function AskView() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.ask(q);
      setMessages((m) => [...m, { role: "ai", text: res.answer, tools: res.tools_used }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "ai", text: err instanceof ApiError ? err.message : "Something went wrong." },
      ]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => scrollRef.current?.scrollTo({ top: 1e9, behavior: "smooth" }));
    }
  }

  return (
    <Card className="flex h-[calc(100vh-12rem)] flex-col">
      <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden p-5">
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Sparkles className="size-6" />
              </div>
              <div>
                <p className="font-medium">Ask about your money</p>
                <p className="text-sm text-muted-foreground">
                  Answers are grounded in your real transactions.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => send(ex)}
                    className="rounded-full border bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "ai" && (
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Sparkles className="size-4" />
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {m.tools && m.tools.length > 0 && (
                    <p className="mt-2 text-[11px] opacity-70">
                      Grounded via: {m.tools.join(", ")}
                    </p>
                  )}
                </div>
                {m.role === "user" && (
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <User className="size-4" />
                  </div>
                )}
              </div>
            ))
          )}
          {busy && (
            <div className="flex gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Sparkles className="size-4" />
              </div>
              <div className="rounded-2xl bg-muted px-4 py-3">
                <span className="flex gap-1">
                  <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
                </span>
              </div>
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your spending, savings, transactions…"
            disabled={busy}
          />
          <Button type="submit" disabled={busy || !input.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
