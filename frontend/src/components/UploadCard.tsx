import { FileUp, Loader2, Plus, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, ApiError, type Account } from "@/lib/api";

function uploadMethodLabel(method: string) {
  if (method === "pdf-llm" || method === "csv-llm") return " (AI-extracted)";
  if (method === "pdf-heuristic") return " (PDF)";
  return "";
}

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("");
  const [addingAccount, setAddingAccount] = useState(false);
  const [accountName, setAccountName] = useState("");
  const [institution, setInstitution] = useState("");
  const [accountType, setAccountType] = useState("checking");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void api.listAccounts().then(setAccounts).catch(() => {});
  }, []);

  async function createAccount() {
    if (!accountName.trim()) return;
    try {
      const account = await api.createAccount({
        name: accountName.trim(),
        type: accountType,
        institution: institution.trim(),
      });
      setAccounts((current) => [...current, account]);
      setAccountId(String(account.id));
      setAccountName("");
      setInstitution("");
      setAddingAccount(false);
    } catch {
      toast.error("Could not add this account.");
    }
  }

  async function handleFile(file: File) {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".csv") && !name.endsWith(".pdf")) {
      toast.error("Please choose a .csv or .pdf file.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.upload(file, accountId ? Number(accountId) : null);
      const how = uploadMethodLabel(result.method);
      toast.success(`Imported ${result.imported} transactions from ${result.filename}${how}`);
      onUploaded();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileUp className="size-4" />
          Upload a statement
        </CardTitle>
        <CardDescription>
          Import a bank or credit-card statement as <strong>CSV or PDF</strong>.
          Transactions are parsed, normalized, and auto-categorized.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="upload-account" className="text-sm font-medium">
            Source account
          </label>
          <div className="flex gap-2">
            <select
              id="upload-account"
              value={accountId}
              onChange={(event) => setAccountId(event.target.value)}
              className="h-9 min-w-0 flex-1 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Use statement filename only</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {[account.institution, account.name, account.type].filter(Boolean).join(" · ")}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAddingAccount((current) => !current)}
              title="Add an account source"
            >
              <Plus className="size-4" />
              Add account
            </Button>
          </div>
          {addingAccount && (
            <div className="grid gap-2 rounded-md border p-3 sm:grid-cols-2">
              <input
                value={accountName}
                onChange={(event) => setAccountName(event.target.value)}
                placeholder="Account name"
                aria-label="Account name"
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <input
                value={institution}
                onChange={(event) => setInstitution(event.target.value)}
                placeholder="Bank or issuer"
                aria-label="Bank or card issuer"
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <select
                value={accountType}
                onChange={(event) => setAccountType(event.target.value)}
                aria-label="Account type"
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="checking">Checking</option>
                <option value="savings">Savings</option>
                <option value="credit">Credit card</option>
                <option value="investment">Investment</option>
                <option value="other">Other</option>
              </select>
              <Button type="button" size="sm" onClick={createAccount} disabled={!accountName.trim()}>
                Save account
              </Button>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
          className={`flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-colors ${
            dragging ? "border-primary bg-accent" : "border-border hover:border-primary/50 hover:bg-accent/50"
          }`}
          disabled={busy}
        >
          {busy ? (
            <Loader2 className="size-8 animate-spin text-primary" />
          ) : (
            <UploadCloud className="size-8 text-muted-foreground" />
          )}
          <div className="text-center">
            <p className="font-medium">{busy ? "Importing…" : "Drag & drop your CSV or PDF here"}</p>
            <p className="text-sm text-muted-foreground">or click to browse files</p>
          </div>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.pdf,text/csv,application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground mb-1">Supported formats</p>
          <strong>CSV:</strong> <code>Date, Description, Amount</code> — or
          separate <code>Debit</code>/<code>Credit</code> columns.{" "}
          <strong>PDF:</strong> statements with a transactions table. Negative
          amounts are spending, positive are income.
        </div>
      </CardContent>
    </Card>
  );
}
