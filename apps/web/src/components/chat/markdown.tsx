"use client";

import { Check, Copy, Loader2, Play } from "lucide-react";
import { createContext, memo, useContext, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { api, type CodeResult, errorMessage } from "@/lib/api";
import { copyText } from "@/lib/text";

/** Lets Python code blocks in answers run in the server's sandbox. */
export const RunContext = createContext<{ canRun: boolean; conversationId: string | null }>({
  canRun: false,
  conversationId: null,
});

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children);
  }
  return "";
}

function RunOutput({ result }: { result: CodeResult }) {
  return (
    <div className="border-t border-white/10 bg-black/30 p-3 text-[12.5px]" aria-live="polite">
      <p className="mb-1 text-[11px] text-slate-400">
        Resultado • {result.duration} s{result.exit_code !== 0 ? ` • saiu com código ${result.exit_code}` : ""}
      </p>
      {result.stdout && <pre className="vx-scroll max-h-72 overflow-auto whitespace-pre-wrap text-slate-100">{result.stdout}</pre>}
      {result.stderr && <pre className="vx-scroll max-h-56 overflow-auto whitespace-pre-wrap text-red-300">{result.stderr}</pre>}
      {!result.stdout && !result.stderr && result.images.length === 0 && (
        <p className="text-slate-400">(sem saída)</p>
      )}
      {result.images.map((img) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={img.id} src={`/api/files/${img.id}/content`} alt="Gráfico gerado" className="mt-2 max-w-full rounded-lg bg-white" />
      ))}
    </div>
  );
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const { canRun, conversationId } = useContext(RunContext);
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CodeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const code = Array.isArray(children) ? children[0] : children;
  const className =
    (code && typeof code === "object" && "props" in code
      ? (code as { props: { className?: string } }).props.className
      : "") ?? "";
  const language = /language-([\w+#-]+)/.exec(className)?.[1] ?? "código";
  const text = textOf(children).replace(/\n$/, "");
  const runnable = canRun && (language === "python" || language === "py");

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setResult(
        await api<CodeResult>("/api/tools/code/run", {
          method: "POST",
          json: { code: text, conversation_id: conversationId },
        }),
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="not-prose overflow-hidden rounded-xl border border-line bg-[var(--code-bg)] text-[13.5px] text-slate-100">
      <div className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-1.5 text-xs text-slate-400">
        <span>{language}</span>
        <span className="flex gap-1">
          {runnable && (
            <button
              type="button"
              onClick={() => void run()}
              disabled={running}
              className="flex items-center gap-1.5 rounded-md px-2 py-1 text-emerald-300 hover:bg-white/10 disabled:opacity-60"
              aria-label="Executar código"
              title="Executa num ambiente isolado do servidor, sem internet"
            >
              {running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />}
              {running ? "Executando…" : "Executar"}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              void copyText(text).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              });
            }}
            className="flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-white/10 hover:text-slate-100"
            aria-label="Copiar código"
          >
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            {copied ? "Copiado" : "Copiar"}
          </button>
        </span>
      </div>
      <pre className="vx-scroll overflow-x-auto p-4 leading-relaxed">{children}</pre>
      {error && <p className="border-t border-white/10 px-4 py-2 text-xs text-red-300">{error}</p>}
      {result && <RunOutput result={result} />}
    </div>
  );
}

export const Markdown = memo(function Markdown({ text }: { text: string }) {
  return (
    <div className="vx-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false }], [rehypeHighlight, { ignoreMissing: true }]]}
        components={{
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
});
