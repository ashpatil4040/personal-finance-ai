import { Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function AuthPage() {
  const { login, register } = useAuth();
  const [busy, setBusy] = useState(false);

  const [loginEmail, setLoginEmail] = useState("demo@financeai.app");
  const [loginPassword, setLoginPassword] = useState("demo1234");

  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await login(loginEmail, loginPassword);
      toast.success("Welcome back!");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await register(regEmail, regPassword, regName);
      toast.success("Account created!");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-primary text-primary-foreground p-12">
        <div className="flex items-center gap-2 font-semibold text-lg">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary-foreground/15">
            <Sparkles className="size-5" />
          </div>
          Finance AI
        </div>
        <div className="space-y-4">
          <h1 className="text-4xl font-bold leading-tight">
            Your money, understood.
          </h1>
          <p className="text-primary-foreground/80 text-lg max-w-md">
            Upload your statements and get automatic categorization, spending
            breakdowns, and plain-language insights — no spreadsheets required.
          </p>
        </div>
        <p className="text-primary-foreground/60 text-sm">
          Phase 1 · Foundation build
        </p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <Card className="w-full max-w-md border-border/60 shadow-sm">
          <CardHeader className="text-center">
            <div className="lg:hidden mx-auto mb-2 flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-5" />
            </div>
            <CardTitle className="text-2xl">Welcome</CardTitle>
            <CardDescription>Sign in to your finance dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">Sign in</TabsTrigger>
                <TabsTrigger value="register">Create account</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={onLogin} className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Password</Label>
                    <Input
                      id="login-password"
                      type="password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={busy}>
                    {busy ? "Signing in…" : "Sign in"}
                  </Button>
                  <p className="text-xs text-muted-foreground text-center">
                    Demo account is pre-filled — just click Sign in.
                  </p>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={onRegister} className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="reg-name">Full name</Label>
                    <Input
                      id="reg-name"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      placeholder="Jane Doe"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-email">Email</Label>
                    <Input
                      id="reg-email"
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-password">Password</Label>
                    <Input
                      id="reg-password"
                      type="password"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={busy}>
                    {busy ? "Creating…" : "Create account"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
