import { Suspense } from "react";
import { ChatScreen } from "@/components/chat/chat-screen";
import { RightPanel } from "@/components/right-panel";

// One persistent chat screen for "/" and "/c/[id]", so sending the first message
// (which creates the conversation and changes the URL) never remounts the stream.
export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full">
      <div className="min-w-0 flex-1">
        <Suspense>
          <ChatScreen />
        </Suspense>
      </div>
      <RightPanel />
      {children}
    </div>
  );
}
