"use client";

import { Check, Copy } from "lucide-react";
import { memo, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { copyText } from "@/lib/text";

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children);
  }
  return "";
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false);
  const code = Array.isArray(children) ? children[0] : children;
  const className =
    (code && typeof code === "object" && "props" in code
      ? (code as { props: { className?: string } }).props.className
      : "") ?? "";
  const language = /language-([\w+#-]+)/.exec(className)?.[1] ?? "código";
  const text = textOf(children).replace(/\n$/, "");

  return (
    <div className="not-prose overflow-hidden rounded-xl border border-line bg-[var(--code-bg)] text-[13.5px] text-slate-100">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-1.5 text-xs text-slate-400">
        <span>{language}</span>
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
      </div>
      <pre className="vx-scroll overflow-x-auto p-4 leading-relaxed">{children}</pre>
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
