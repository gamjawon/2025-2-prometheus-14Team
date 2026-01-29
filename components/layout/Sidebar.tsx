"use client";

import Image from "next/image";
import Link from "next/link";
import Button from "@/components/ui/Button";
import React, { useMemo, useState } from "react";

type SidebarItem = {
  icon: "folder" | "chat";
  label: string;
  active?: boolean;
  onClick?: () => void;
};

type SidebarSection = {
  title: string;
  items: SidebarItem[];
};

type Props = {
  brandLabel?: string;
  logoSrc?: string;
  topToggleIconSrc?: string;
  userIconSrc?: string;
  nickname?: string;
  onNewChat?: () => void;
  labSections?: SidebarSection;
  recentSections?: SidebarSection;
};

export default function Sidebar({
  brandLabel = "AItom",
  logoSrc = "/logo.svg",
  topToggleIconSrc = "/chaticon/Icon.svg",
  userIconSrc = "/chaticon/user.svg",
  nickname = "닉네임",
  onNewChat,
  labSections,
  recentSections,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);

  const lab = useMemo<SidebarSection>(() => {
    return (
      labSections ?? {
        title: "내 LAB 폴더",
        items: [
          { icon: "folder", label: "개인 연구" },
          { icon: "folder", label: "개인 연구" },
          { icon: "folder", label: "개인 연구" },
        ],
      }
    );
  }, [labSections]);

  const recent = useMemo<SidebarSection>(() => {
    return (
      recentSections ?? {
        title: "최근 대화",
        items: [
          { icon: "chat", label: "TiO2 나노입자 합성", active: true },
          { icon: "chat", label: "ZnO 박막 제조" },
          { icon: "chat", label: "ZnO 박막 제조" },
        ],
      }
    );
  }, [recentSections]);

  return (
    <aside
      className={[
        // ✅ 핵심: min-h-dvh로 “화면 높이”를 강제로 잡아야 mt-auto가 바닥으로 내려감
        "flex flex-col min-h-dvh border-r border-slate-100 bg-white transition-all duration-300 overflow-hidden",
        // ✅ 로고 위/닉네임 아래 49px 정확히
        "pt-[49px] pb-[49px]",
        collapsed ? "w-[56px] px-2" : "w-[240px] px-5",
      ].join(" ")}
    >
      {collapsed ? (
        <div className="flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            className="grid h-10 w-10 place-items-center rounded-md hover:bg-slate-50"
            aria-label="사이드바 펼치기"
          >
            <Image
              src={topToggleIconSrc}
              alt=""
              width={24}
              height={24}
              className="h-6 w-6"
              priority
            />
          </button>
        </div>
      ) : (
        <>
          {/* 상단: 로고 + 토글 아이콘 */}
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center">
              <Image
                src={logoSrc}
                alt={brandLabel}
                width={107}
                height={26}
                priority
                className="h-auto w-[84px] lg:w-[107px]"
              />
            </Link>

            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="grid h-9 w-9 place-items-center rounded-md hover:bg-slate-50"
              aria-label="사이드바 접기"
            >
              <Image
                src={topToggleIconSrc}
                alt=""
                width={24}
                height={24}
                className="h-6 w-6"
                priority
              />
            </button>
          </div>

          <Button
            variant="gradient"
            className="mt-[29px] w-full text-[15px] py-[14px] rounded-[30px]"
            onClick={onNewChat}
          >
            새 채팅
          </Button>

          <div className="mt-[47px]">
            <Image
              src="/chaticon/bar.svg"
              alt=""
              width={222}
              height={6}
              className="h-[6px] w-full"
              priority
            />
          </div>

          <div className="mt-[18px] border-b border-slate-100 pb-6" />

          {/* 내 LAB 폴더 */}
          <Section title={lab.title}>
            {lab.items.map((it, idx) => (
              <SideItem
                key={`${it.label}-${idx}`}
                icon={it.icon}
                label={it.label}
                active={it.active}
                onClick={it.onClick}
              />
            ))}
          </Section>

          <div className="mt-[61px]" />

          {/* 최근 대화 */}
          <Section title={recent.title}>
            {recent.items.map((it, idx) => (
              <SideItem
                key={`${it.label}-${idx}`}
                icon={it.icon}
                label={it.label}
                active={it.active}
                onClick={it.onClick}
              />
            ))}
          </Section>

          {/* ✅ 하단 사용자: mt-auto로 “진짜 바닥”에 붙음 (pb-[49px]은 aside에 있음) */}
          <div className="mt-auto flex justify-center">
            <div className="flex items-center gap-3 text-[18px] text-slate-700">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-slate-100">
                <Image src={userIconSrc} alt="" width={24} height={24} />
              </div>
              <span>{nickname}</span>
            </div>
          </div>
        </>
      )}
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <div className="flex items-center justify-between text-[16px] text-coolgray60">
        <span>{title}</span>
        <span className="text-coolgray60">⌃</span>
      </div>
      <div className="mt-4 space-y-2">{children}</div>
    </div>
  );
}

function SideItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: "folder" | "chat";
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  const iconSrc = icon === "folder" ? "/chaticon/folder.svg" : "/chaticon/chat.svg";

  return (
    <button
      onClick={onClick}
      className={[
        "w-full rounded-[12px] px-3 py-2 text-left text-[16px] transition",
        active ? "bg-slate-50 text-slate-700" : "text-slate-500 hover:bg-slate-50",
      ].join(" ")}
    >
      <div className="flex items-center gap-3">
        <Image
          src={iconSrc}
          alt=""
          width={18}
          height={18}
          className="h-[18px] w-[18px] opacity-70"
        />
        <span className="truncate">{label}</span>
      </div>
    </button>
  );
}
