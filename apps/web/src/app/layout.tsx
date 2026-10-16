import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vortex",
  description: "Muito mais que um chatbot. Um universo de possibilidades.",
  icons: { icon: "/vortex.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
