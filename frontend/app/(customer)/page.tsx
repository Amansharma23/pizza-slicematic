import { ChatThread } from "@/components/chat/chat-thread";

// Home = the live chat thread. Voice is an input modality into this same
// pipeline (added in the voice milestone), not a separate mode.
export default function ChatHomePage() {
  return <ChatThread />;
}
