"use client";

import Image from "next/image";

export default function SafetyCheckModal({
  open,
  onClose,
  onAcknowledge,
}: {
  open: boolean;
  onClose: () => void;
  onAcknowledge: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60]">
      {/* dim */}
      <button
        className="absolute inset-0 bg-black/25"
        onClick={onClose}
        aria-label="close"
      />

      {/* modal */}
      <div className="absolute left-1/2 top-1/2 w-[540px] -translate-x-1/2 -translate-y-1/2 rounded-[14px] bg-white px-7 py-6 shadow-[0_30px_80px_rgba(0,0,0,0.22)]">
        <div className="text-center">
          <div className="mx-auto mb-2 flex items-center justify-center gap-2 text-[32px] font-semibold text-[#EC3300]">
            <Image
              src="/chaticon/graphic.svg"
              alt=""
              width={45}
              height={45}
              className=""
                        />
            <span>Safety Check</span>
          </div>

          <div className="mt-8 text-[18px] leading-relaxed font-semibold text-slate-600">
            TiO2와 같은 화학물질 관련 내용은
            <br />
            안전수칙 확인이 필요합니다.
          </div>

          <div className="mx-auto mt-[18px] rounded-[12px] border border-[#FFD6D6] bg-[#FFF7F7] px-4 py-3 text-left text-[16px] text-coolgray80">
            <ul className="list-disc space-y-1 pl-4">
              <li>환기/보호구 착용을 확인하세요</li>
              <li>불명확한 단계는 전문가에게 문의</li>
              <li>위험 단계가 있으면 안내를 따르세요</li>
            </ul>
          </div>

          <button
            onClick={onAcknowledge}
            className="mt-[50px] w-full rounded-full bg-[linear-gradient(180deg,#7EBBFF_0%,#4EA6FF_100%)] py-3 text-[16px] font-semibold text-white shadow-[0_10px_24px_rgba(78,166,255,0.25)]"
          >
            확인했습니다
          </button>
        </div>
      </div>
    </div>
  );
}
