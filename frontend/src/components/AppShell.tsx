import {
  LayoutDashboard,
  ListChecks,
  LogOut,
  Sparkles,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Insights, type Transaction } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CategoryChart, MonthlyChart } from "./Charts";
import { InsightsPanel } from "./InsightsPanel";
import { StatCards } from "./StatCards";
import { TransactionsTable } from "./TransactionsTable";
import { UploadCard } from "./UploadCard";

type View = "dashboard" | "transactions" | "upload";

const NAV: { id: View; label: string; icon: React.ReactNode }[] = [
  { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="size-4" /> },
  { id: "transactions", label: "Transactions", icon: <ListChecks className="size-4" /> },
  { id: "upload", label: "Upload", icon: <Upload className="size-4" /> },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const [view, setView] = useState<View>("dashboard");
  const [insights, setInsights] = useState<Insights | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [ins, txns] = await Promise.all([api.insights(), api.listTransactions()]);
      setInsights(ins);
      setTransactions(txns);
    } catch {
      toast.error("Could not load your data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onDelete(id: number) {
    try {
      await api.deleteTransaction(id);
      toast.success("Transaction deleted");
      refresh();
    } catch {
      toast.error("Delete failed");
    }
  }

  const initials =
    (user?.full_name || user?.email || "?")
      .split(" ")
      .map((s) => s[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?";

  return (
    <div className="min-h-screen bg-muted/30">
      <div className="mx-auto flex max-w-[1400px]">
        {/* Sidebar */}
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-background p-4 md:flex">
          <div className="flex items-center gap-2 px-2 py-3 font-semibold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </div>
            Finance AI
          </div>
          <nav className="mt-4 flex flex-1 flex-col gap-1">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  view === item.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-3 border-t pt-3">
            <Avatar className="size-9">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.full_name || "User"}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Sign out">
              <LogOut className="size-4" />
            </Button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 p-5 sm:p-8">
          {/* Mobile nav */}
          <div className="mb-4 flex gap-2 md:hidden">
            {NAV.map((item) => (
              <Button
                key={item.id}
                variant={view === item.id ? "default" : "outline"}
                size="sm"
                onClick={() => setView(item.id)}
              >
                {item.icon}
                <span className="ml-1">{item.label}</span>
              </Button>
            ))}
          </div>

          <header className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold capitalize">{view}</h1>
              <p className="text-sm text-muted-foreground">
                {view === "dashboard" && "Your financial overview at a glance."}
                {view === "transactions" && "Every transaction, auto-categorized."}
                {view === "upload" && "Import statements to grow your history."}
              </p>
            </div>
            <Button variant="ghost" size="icon" onClick={logout} className="md:hidden" aria-label="Sign out">
              <LogOut className="size-4" />
            </Button>
          </header>

          {loading ? (
            <LoadingState />
          ) : view === "dashboard" ? (
            <DashboardView insights={insights} transactions={transactions} />
          ) : view === "transactions" ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">All transactions ({transactions.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <TransactionsTable transactions={transactions} onDelete={onDelete} />
              </CardContent>
            </Card>
          ) : (
            <div className="max-w-xl">
              <UploadCard
                onUploaded={() => {
                  refresh();
                  setView("dashboard");
                }}
              />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function DashboardView({
  insights,
  transactions,
}: {
  insights: Insights | null;
  transactions: Transaction[];
}) {
  if (!insights) return null;
  return (
    <div className="space-y-6">
      <StatCards summary={insights.summary} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Spending by category</CardTitle>
          </CardHeader>
          <CardContent>
            <CategoryChart data={insights.spending_by_category} />
          </CardContent>
        </Card>
        <InsightsPanel insights={insights.insights} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Monthly spending</CardTitle>
          </CardHeader>
          <CardContent>
            <MonthlyChart data={insights.monthly_spending} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent transactions</CardTitle>
          </CardHeader>
          <CardContent>
            <TransactionsTable transactions={transactions.slice(0, 6)} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-72 rounded-xl lg:col-span-2" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </div>
  );
}
