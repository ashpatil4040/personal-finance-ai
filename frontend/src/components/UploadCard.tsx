import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast.error("Please choose a .csv file.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.upload(file);
      toast.success(`Imported ${result.imported} transactions from ${result.filename}`);
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
          Import a bank or credit-card CSV export. Transactions are parsed,
          normalized, and auto-categorized.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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
            <p className="font-medium">{busy ? "Importing…" : "Drag & drop your CSV here"}</p>
            <p className="text-sm text-muted-foreground">or click to browse files</p>
          </div>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground mb-1">Expected columns</p>
          <code>Date, Description, Amount</code> — or separate{" "}
          <code>Debit</code>/<code>Credit</code> columns. Negative amounts are
          spending, positive are income.
        </div>
      </CardContent>
    </Card>
  );
}
