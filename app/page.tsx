import Chat from "@/components/Chat";

/** `/` is always a fresh conversation; it moves to /c/<session_id> after the first answer. */
export default function NewChatPage() {
  return <Chat key="new" />;
}
