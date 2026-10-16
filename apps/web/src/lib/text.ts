/** Split "<think>…</think>answer" into the reasoning and the visible answer. */
export function splitThinking(content: string): { thinking: string; answer: string; open: boolean } {
  const start = content.indexOf("<think>");
  if (start === -1) return { thinking: "", answer: content, open: false };
  const end = content.indexOf("</think>", start);
  if (end === -1) {
    return { thinking: content.slice(start + 7).trim(), answer: content.slice(0, start), open: true };
  }
  return {
    thinking: content.slice(start + 7, end).trim(),
    answer: (content.slice(0, start) + content.slice(end + 8)).trim(),
    open: false,
  };
}

/** Clipboard that also works on plain http:// LAN addresses (no secure context). */
export async function copyText(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "agora";
  if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `há ${Math.floor(diff / 3600)}h`;
  const days = Math.floor(diff / 86400);
  return days === 1 ? "há 1 dia" : `há ${days} dias`;
}
