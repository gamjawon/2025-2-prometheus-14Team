import React from "react";

type Props = {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost" | "gradient";
  className?: string;
  disabled?: boolean;
  type?: "button" | "submit";
};

export default function Button({
  children,
  onClick,
  variant = "primary",
  className = "",
  disabled,
  type = "button",
}: Props) {
  const base =
    "inline-flex items-center justify-center rounded-2xl px-5 py-3 font-semibold transition disabled:opacity-60 disabled:cursor-not-allowed";

  const style =
    variant === "gradient"
      ? [
          "text-white",
          "bg-gradient-to-bl from-sky-200 via-blue-400 to-blue-300",
          "shadow-[inset_-2.6911px_-5.3823px_15.474px_rgba(0,4,117,0.15),inset_4.0367px_4.0367px_9.5px_rgba(255,255,255,0.47)]",
          "outline outline-[1.35px] outline-offset-[-1.35px] outline-white/20",
          "hover:brightness-[0.98]",
          "active:brightness-[0.96]",
        ].join(" ")
      : variant === "primary"
      ? "bg-blue-500 text-white hover:bg-blue-600"
      : "bg-coolgray-10 text-slate-700 hover:bg-slate-50 border border-slate-200";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${style} ${className}`}
    >
      {children}
    </button>
  );
}
