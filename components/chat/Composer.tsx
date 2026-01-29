"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

export default function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  }

  const sendDisabled = disabled || value.trim().length === 0;

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        disabled={disabled}
        placeholder="메시지를 입력하세요."
        className="h-10 flex-1 bg-transparent px-2 text-[18px] text-slate-600 placeholder:text-slate-300 outline-none disabled:opacity-60"
      />

      <button
        type="button"
        onClick={submit}
        disabled={sendDisabled}
        className={[
          "relative grid h-10 w-10 place-items-center",
          "transition",
          "disabled:opacity-40",
        ].join(" ")}
        aria-label="send"
      >
        {/* 배경 원 (Ellipse 2.svg) */}
        <Image
          src="/chaticon/Ellipse 2.svg"
          alt=""
          width={40}
          height={40}
          className="absolute inset-0 h-full w-full"
          priority
        />

        {/* 전송 아이콘 (send.svg) */}
        <Image
          src="/chaticon/send.svg"
          alt=""
          width={18}
          height={18}
          className="relative h-[18px] w-[18px]"
          priority
        />
      </button>
    </div>
  );
}
