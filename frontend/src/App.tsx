import { Loader2 } from "lucide-react";
import { AppShell } from "./components/AppShell";
import { AuthPage } from "./components/AuthPage";
import { useAuth } from "./lib/auth";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return user ? <AppShell /> : <AuthPage />;
}
