import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, FileText, Loader2, RotateCcw, Upload, X } from "lucide-react";
import { toast } from "sonner";

const ACCEPT = ".csv,.xls,.xlsx,.txt,.json";
const ALLOWED = /\.(csv|xls|xlsx|txt|json)$/i;

function iconFor(name: string) {
  return /\.(txt|json)$/i.test(name) ? FileText : FileSpreadsheet;
}

function sizeOf(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

type UploadResult = {
  summary?: unknown;
  passes?: unknown;
  all_exceptions?: unknown;
  graph?: { nodes?: unknown[]; edges?: unknown[] };
  forecast?: unknown;
};

export function UploadPanel() {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  function applyResult(data: UploadResult) {
    if (data.summary) queryClient.setQueryData(["summary"], data.summary);
    if (data.passes) queryClient.setQueryData(["passes"], data.passes);
    if (data.forecast) queryClient.setQueryData(["forecast"], data.forecast);
    if (Array.isArray(data.all_exceptions)) {
      queryClient.setQueryData(["exceptions"], {
        count: data.all_exceptions.length,
        exceptions: data.all_exceptions,
      });
    }
    if (data.graph?.nodes && data.graph?.edges) {
      queryClient.setQueryData(["graph"], data.graph);
    }
    void queryClient.invalidateQueries();
  }

  const upload = useMutation({
    mutationFn: async (selected: File[]) => {
      const form = new FormData();
      for (const f of selected) form.append("files", f, f.name);
      const res = await fetch("/api/proxy/upload", { method: "POST", body: form });
      if (res.status === 404 || res.status === 405) {
        throw new Error(
          "The pipeline service isn't accepting uploaded files yet — it still reads the built-in sample files.",
        );
      }
      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      return (await res.json().catch(() => ({}))) as UploadResult;
    },
    onSuccess: (data) => {
      applyResult(data);
      setFiles([]);
      toast.success("Files uploaded — results refreshed");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const reset = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/proxy/data/reset", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      });
      if (!res.ok) throw new Error(`Reset failed (${res.status})`);
      return (await res.json().catch(() => ({}))) as UploadResult;
    },
    onSuccess: (data) => {
      applyResult(data);
      setFiles([]);
      toast.success("Back to the sample data");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  function add(list: FileList | null) {
    if (!list) return;
    const allowed = Array.from(list).filter((f) => ALLOWED.test(f.name));
    if (allowed.length !== (list?.length ?? 0)) {
      toast.error("Only CSV, Excel, TXT and JSON files are supported");
    }
    setFiles((prev) => [...prev, ...allowed]);
  }


  return (
    <div className="panel p-7">
      <h2 className="text-xl font-semibold text-foreground">Provide your own data</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Drop in your settlement report, bank statement, GST invoices, sales ledger or reserve
        ledger. CSV, Excel, TXT and JSON are all accepted.
      </p>


      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          add(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={`mt-6 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? "border-foreground bg-accent/50"
            : "border-border hover:border-foreground/50 hover:bg-accent/30"
        }`}
      >
        <Upload className="size-5 text-muted-foreground" aria-hidden />
        <p className="mt-3 text-sm text-foreground">Drag files here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">CSV · XLS · XLSX · TXT · JSON</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((f, i) => {
            const Icon = iconFor(f.name);
            return (
              <li
                key={`${f.name}-${i}`}
                className="flex items-center gap-3 rounded-md border border-border bg-background/40 px-3 py-2"
              >
                <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span className="truncate text-xs text-foreground">{f.name}</span>
                <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                  {sizeOf(f.size)}
                </span>
                <button
                  type="button"
                  aria-label={`Remove ${f.name}`}
                  onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={files.length === 0 || upload.isPending}
          onClick={() => upload.mutate(files)}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-foreground px-6 py-2.5 text-sm font-medium text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
        >
          {upload.isPending ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
          {upload.isPending ? "Uploading…" : "Upload & run pipeline"}
        </button>
        <button
          type="button"
          disabled={reset.isPending}
          onClick={() => reset.mutate()}
          className="inline-flex items-center gap-2 rounded-full border border-border px-6 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
        >
          {reset.isPending ? <Loader2 className="size-4 animate-spin" /> : <RotateCcw className="size-4" />}
          Reset to demo data
        </button>
      </div>

    </div>
  );
}
