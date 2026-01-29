"use client";

import Sidebar from "@/components/layout/Sidebar";

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-white">
      <div className="flex min-h-dvh">
        <Sidebar />
        <main className="flex-1 bg-[#F6F8FC]">{children}</main>
      </div>
    </div>
  );
}
