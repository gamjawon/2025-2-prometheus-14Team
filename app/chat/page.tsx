"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import MessageBubble, { ChatMsg } from "@/components/chat/MessageBubble";
import Composer from "@/components/chat/Composer";
import SafetyCheckModal from "@/components/chat/SafetyCheckModal";
import Sidebar from "@/components/layout/Sidebar";
import Image from "next/image";

function uid() {
  return Math.random().toString(36).slice(2);
}

export default function Page() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [safetyOpen, setSafetyOpen] = useState(false);

  const [activeTitle, setActiveTitle] = useState("새 채팅");

  const listRef = useRef<HTMLDivElement | null>(null);

  const allowStreamRef = useRef(true);      // 모달 열리면 false로 해서 화면 반영 막기
  const bufferRef = useRef("");             // 모달 동안 들어오는 텍스트를 임시 저장
  const activeBotIdRef = useRef<string | null>(null); // 현재 스트리밍 중인 botMsg id


  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isStreaming, safetyOpen]);

  async function send(text: string) {
    const userMsg: ChatMsg = { id: uid(), role: "user", kind: "text", text };
    const botMsg: ChatMsg = { id: uid(), role: "assistant", kind: "text", text: "" };

    allowStreamRef.current = true;
    bufferRef.current = "";
    activeBotIdRef.current = botMsg.id;

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setIsStreaming(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.body) throw new Error("No stream body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        // ✅ 토큰이 chunk 중간에 섞여도 텍스트가 안 날아가도록 분리
        const token = "[SAFETY_CHECK]";
        const hasToken = chunk.includes(token);
        const safeChunk = chunk.split(token).join(""); // 토큰만 제거한 나머지

        if (hasToken) {
          setSafetyOpen(true);
          allowStreamRef.current = false;
        }

        // ✅ 모달이 열려있으면 화면에 붙이지 말고 버퍼에만 저장
        if (!allowStreamRef.current) {
          bufferRef.current += safeChunk;
          continue;
        }

        // ✅ 정상 스트리밍이면 바로 botMsg에 append
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsg.id ? { ...m, text: m.text + safeChunk } : m
          )
        );
      }

    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsg.id ? { ...m, text: "에러가 발생했어요. 다시 시도해주세요." } : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }

  const empty = useMemo(() => messages.length === 0, [messages.length]);

  return (
    <div className="h-dvh overflow-hidden bg-white">
      <div className="flex h-dvh overflow-hidden">
        <Sidebar
          brandLabel="AItom"
          logoSrc="/logo.svg"
          topToggleIconSrc="/chaticon/Icon.svg"
          userIconSrc="/chaticon/user.svg"
          nickname="닉네임"
          onNewChat={() => {
            setMessages([]);
            setSafetyOpen(false);
            setActiveTitle("새 채팅");
          }}
          labSections={{
            title: "내 LAB 폴더",
            items: [
              { icon: "folder", label: "개인 연구" },
              { icon: "folder", label: "개인 연구" },
              { icon: "folder", label: "개인 연구" },
            ],
          }}
          recentSections={{
            title: "최근 대화",
            items: [
              {
                icon: "chat",
                label: "TiO2 나노입자 합성",
                active: activeTitle === "TiO2 나노입자 합성",
                onClick: () => setActiveTitle("TiO2 나노입자 합성"),
              },
              {
                icon: "chat",
                label: "ZnO 박막 제조",
                active: activeTitle === "ZnO 박막 제조",
                onClick: () => setActiveTitle("ZnO 박막 제조"),
              },
              {
                icon: "chat",
                label: "ZnO 박막 제조",
                active: activeTitle === "ZnO 박막 제조(2)",
                onClick: () => setActiveTitle("ZnO 박막 제조(2)"),
              },
            ],
          }}
        />

        {/* 메인 */}
        <main className="flex flex-1 flex-col bg-[#F6F8FC] overflow-hidden">
          {/* 상단바 */}
          <div className="flex h-[92px] items-center gap-3 border-b border-slate-100 bg-white px-6 text-[24px]">
            <Image
              src="/chaticon/chat.svg"
              alt=""
              width={24}
              height={24}
              className="h-6 w-6"
            />
            <span className=" text-black">{activeTitle}</span>
          </div>

          {/* 메시지 영역 */}
          <div ref={listRef} className="flex-1 overflow-y-auto overflow-x-hidden px-10 py-10">
            {empty ? (
              <EmptyState />
            ) : (
              <div className="mx-auto w-full max-w-[1200px] space-y-6">
                {messages.map((m) => (
                  <MessageBubble key={m.id} msg={m} />
                ))}
              </div>
            )}
          </div>

          {/* 하단 입력창 */}
          <div className="px-10 pb-8">
            <div className="mx-auto w-full max-w-[980px]">
              <div className="rounded-[39px] bg-white px-4 py-3 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
                <Composer onSend={send} disabled={isStreaming || safetyOpen} />
              </div>
              
            </div>
          </div>
        </main>
      </div>

      {/* Safety Check 모달 */}
      <SafetyCheckModal
        open={safetyOpen}
        onClose={() => setSafetyOpen(false)}
        onAcknowledge={() => {
          setSafetyOpen(false);

          const botId = activeBotIdRef.current;
          const buffered = bufferRef.current;

          // 1) SafetyNotice를 botMsg "앞"에 삽입
          setMessages((prev) => {
            if (!botId) return prev;

            const idx = prev.findIndex((m) => m.id === botId);
            if (idx === -1) return prev;

            const safetyMsg: ChatMsg = {
              id: uid(),
              role: "assistant",
              kind: "safety_notice",
              text:
                "화학물질을 다루는 내용은 안전수칙이 반드시 필요합니다.\n" +
                "도구/환기/보호구 등 안전장비를 사용하고, 위험 단계가 포함되면 전문가에게 확인하세요.",
            };

            const next = [...prev];
            next.splice(idx, 0, safetyMsg); // ✅ botMsg 앞에 끼워넣기
            return next;
          });

          // 2) 버퍼에 쌓인 합성법 텍스트를 botMsg에 한 번에 붙이기
          if (botId && buffered) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId ? { ...m, text: m.text + buffered } : m
              )
            );
          }

          // 3) 이제부터는 스트리밍 텍스트를 다시 화면에 반영
          bufferRef.current = "";
          allowStreamRef.current = true;
        }}

      />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center text-center">
        <div className="mb-[48px] text-slate-300">
          <Image src="/chaticon/채팅 시작.svg" alt="" width={226} height={197} />
          
        </div>
        <div className="text-[32px] text-slate-500">
          궁금한 합성법을 입력해주세요!
        </div>
      </div>
    </div>
  );
}
