"use client";

type RecipeCardProps = {
  title?: string;
  description?: string;
  particleSize?: string;
  createdAt?: string;
  onClick?: () => void;
};

export default function RecipeCard({
  title = "TTIP Sol-gel 합성법",
  description = "티타늄 이소프로폭사이드를 이용한 기본 sol-gel 공정입니다.",
  particleSize = "10~15nm",
  createdAt = "2025. 01. 15",
  onClick,
}: RecipeCardProps) {
  return (
    <div
      onClick={onClick}
      className="group relative cursor-pointer rounded-[14px] bg-white p-5 shadow-[0_14px_28px_rgba(15,23,42,0.06)] transition hover:shadow-[0_20px_36px_rgba(15,23,42,0.10)]"
    >
      {/* 제목 */}
      <div className="text-[13px] font-semibold text-slate-800">
        {title}
      </div>

      {/* 설명 */}
      <div className="mt-2 text-[12px] leading-relaxed text-slate-500">
        {description}
        <br />
        <span className="text-slate-600">입자 크기: {particleSize}</span>
      </div>

      {/* 생성일 */}
      <div className="mt-3 text-[11px] text-slate-400">
        생성일: {createdAt}
      </div>

      {/* 우측 하단 화살표 버튼 */}
      <div className="absolute bottom-4 right-4 grid h-8 w-8 place-items-center rounded-[10px] bg-slate-50 text-slate-400 transition group-hover:bg-[#EEF5FF] group-hover:text-[#4EA6FF]">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
        >
          <path
            d="M9 6l6 6-6 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}
