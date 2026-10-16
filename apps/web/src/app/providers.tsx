"use client";

import { ThemeProvider } from "@/components/theme";
import { SessionProvider } from "@/components/session";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <SessionProvider>{children}</SessionProvider>
    </ThemeProvider>
  );
}
