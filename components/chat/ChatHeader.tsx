"use client";

type ChatHeaderProps = {
  title: string;
  leftIcon?: React.ReactNode;
};

export default function ChatHeader({ title, leftIcon }: ChatHeaderProps) {
  return (
    <div className="flex h-12 items-center gap-3 border-b border-slate-100 bg-white px-6 text-[12px]">
      <span className="text-slate-400">
        {leftIcon ?? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M10.5 18.5a8 8 0 1 1 0-16 8 8 0 0 1 0 16Z"
              stroke="currentColor"
              strokeWidth="2"
            />
            <path
              d="M16.5 16.5 21 21"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        )}
      </span>

      <span className="font-semibold text-slate-700">{title}</span>
    </div>
  );
}
