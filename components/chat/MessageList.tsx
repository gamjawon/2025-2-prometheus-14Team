"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "@/components/chat/MessageBubble";

export type Msg = { id: string; role: "user" | "assistant"; text: string };

type MessageListProps = {
  messages: Msg[];
  isStreaming?: boolean;
};

export default function MessageList({ messages, isStreaming }: MessageListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isStreaming]);

  return (
    <div ref={listRef} className="flex-1 overflow-auto px-10 py-10">
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="mx-auto w-full max-w-[980px] space-y-6">
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} text={m.text} />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center text-center">
        <div className="mb-6 grid h-[150px] w-[220px] place-items-center rounded-3xl bg-white shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <div className="flex items-center gap-6 opacity-80">
            <div className="h-[90px] w-[70px] rounded-2xl bg-[#D6EAFF]" />
            <div className="relative h-[46px] w-[76px] rounded-full bg-[#EEF6FF]">
              <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 gap-2">
                <div className="h-[6px] w-[6px] rounded-full bg-[#9BCBFF]" />
                <div className="h-[6px] w-[6px] rounded-full bg-[#9BCBFF]" />
                <div className="h-[6px] w-[6px] rounded-full bg-[#9BCBFF]" />
              </div>
            </div>
          </div>
        </div>

        <div className="text-[14px] font-semibold text-slate-500">
          궁금한 합성법을 입력해주세요!
        </div>
      </div>
    </div>
  );
}
