"use client";

import Image from "next/image";

export type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  kind: "text" | "safety_notice";
  text: string;
};

export default function MessageBubble({ msg }: { msg: ChatMsg }) {
  if (msg.kind === "safety_notice") return <SafetyNotice text={msg.text} />;

  if (msg.role === "user") return <UserBubble text={msg.text} />;

  return <AssistantCard text={msg.text} />;
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[520px] rounded-[14px] bg-slate-200 px-4 py-3 text-[15px] leading-relaxed text-slate-600">
        {text}
      </div>
    </div>
  );
}

function AssistantCard({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      {/* 카드 전체 컨테이너 */}
      <div className="relative max-w-[560px]">
        {/* ✅ 바깥 그라데이션 테두리/오라 느낌 */}
        <div className="absolute inset-0 rounded-[14px] bg-[linear-gradient(135deg,#A9FFEB_0%,#73CCF7_35%,#4FAAFF_70%,#A2D3FF_100%)] opacity-[0.22]" />

        {/* ✅ 실제 카드 본체 (흰 배경) */}
        <div className="relative rounded-[14px] bg-white px-5 py-4 shadow-[0_14px_28px_rgba(15,23,42,0.06)]">
          {/* ✅ 좌상단 SVG 심볼 */}
          <div className="absolute">
            <Image
              src="/symbol.svg"
              alt=""
              width={34}
              height={34}
              className="h-[34px] w-[34px]"
              priority
            />
          </div>

          {/* 본문 텍스트 */}
          <div className="mt-11 text-[15px] leading-relaxed text-slate-700 whitespace-pre-wrap">
            {text || " "}
          </div>

          {/* ✅ 서브 박스(피그마 느낌: 연한 파랑 박스 + 보더) */}
          <div className="mt-3 rounded-[12px] border border-[#C5E4FF] bg-[#F2FCFF] px-4 py-3 text-[14px] text-slate-600">
            <div className="font-semibold text-[#4FAAFF]">TTIP 기반 sol-gel 합성법</div>
            <ul className="mt-2 list-disc pl-4 space-y-1">
              <li>전구체: 티타늄 이소프로폭사이드</li>
              <li>용매: 에탄올</li>
              <li>반응 온도: 60~80도</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function SafetyNotice({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[560px] rounded-[14px] border border-white bg-white px-5 py-4 shadow-[0_14px_28px_rgba(15,23,42,0.06)]">
        <div className="flex items-center gap-2 text-[15px] font-semibold text-slate-700">
          <Image
            src="/chaticon/graphic.svg"
            alt=""
            width={40}
            height={40}
            className=""
                       />

        </div>

        <div className="mt-2 text-[15px] leading-relaxed text-slate-700 whitespace-pre-wrap">
          {text}
        </div>

        <div className="mt-3 rounded-[10px] border border-[#FFD6D6] bg-[#FFF3F3] px-4 py-3 text-[15px] text-slate-700">
          <ul className="list-disc pl-4 space-y-1">
            <li>환기/보호구/화학물질 취급수칙 준수</li>
            <li>위험 단계 포함 시 전문가/지도자 확인</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
