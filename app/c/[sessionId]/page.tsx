import { Suspense } from "react";
import Chat from "@/components/Chat";

/**
 * A specific conversation window: /c/<session_id>.
 * With cacheComponents enabled, runtime params must be read inside <Suspense>.
 */
export default function ConversationPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  return (
    <Suspense fallback={<ChatFallback />}>
      {params.then(({ sessionId }) => (
        <Chat key={sessionId} sessionId={sessionId} />
      ))}
    </Suspense>
  );
}

function ChatFallback() {
  return (
    <div className="flex h-full max-w-3xl mx-auto flex-col px-4 sm:px-6 py-5 gap-6">
      <div className="skeleton h-6 w-56" />
      <div className="flex justify-end"><div className="skeleton h-11 w-2/5 rounded-2xl" /></div>
      <div className="flex gap-3"><div className="skeleton size-8 rounded-xl" /><div className="skeleton h-24 flex-1 rounded-2xl" /></div>
    </div>
  );
}
