import { ApiStatus } from "@/components/api-status";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-6 px-4 py-16 text-center">
      <img src="/vortex.svg" alt="" width={120} height={120} className="drop-shadow-[0_0_30px_rgba(99,102,241,0.6)]" />
      <h1 className="bg-gradient-to-b from-white to-blue-300 bg-clip-text text-6xl font-light tracking-[0.3em] text-transparent">
        VORTEX
      </h1>
      <p className="text-2xl text-blue-200">v0.2.1</p>
      <p className="text-lg text-vx-muted">Muito mais que um chatbot. Um universo de possibilidades.</p>
      <ApiStatus />
      <p className="text-sm text-vx-muted">
        Interface completa de chat chega na etapa 3. Por enquanto, use a API em{" "}
        <code className="text-blue-300">/docs</code>.
      </p>
    </main>
  );
}
