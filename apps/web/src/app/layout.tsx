import type { Metadata, Viewport } from "next";
import "katex/dist/katex.min.css";
import "highlight.js/styles/github-dark.css";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Vortex",
  description: "Muito mais que um chatbot. Um universo de possibilidades.",
  icons: { icon: "/vortex.svg" },
};

export const viewport: Viewport = {
  themeColor: "#04070f",
  width: "device-width",
  initialScale: 1,
};

// Applies the saved theme before first paint (no flash of the wrong theme).
const themeScript = `try{var t=localStorage.getItem("vortex-theme");if(t==="light")document.documentElement.dataset.theme="light"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
