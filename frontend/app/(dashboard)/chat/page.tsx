import { Header } from "@/components/shared/Header";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="AI Chat"
        subtitle="Multi-agent financial assistant"
      />
      <div className="flex-1 overflow-hidden">
        <ChatWindow />
      </div>
    </div>
  );
}
