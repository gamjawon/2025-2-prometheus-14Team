"use client";

import PublicHeader from "@/components/layout/PublicHeader";
import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "../../services/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (loading) return;

    try {
      setLoading(true);
      const res = await register({ username, password });
      alert(res?.message ?? "회원가입이 완료되었습니다.");
      router.push("/login");
    } catch (err: any) {
      alert(err?.message ?? "회원가입 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh bg-[linear-gradient(250deg,#F2F8F8_12.1%,#F2FCFF_48.17%,#E5F3F3_84.93%)]">
      <PublicHeader hideAuthButtons />

      <main className="mx-auto flex max-w-[1440px] justify-center px-6 py-[80px]">
        <div className="w-full max-w-[703px] h-[657px] rounded-[20px] bg-white px-[115px] py-[67px] shadow-[0px_0px_30px_rgba(0,0,0,0.06)]">
          <div className="mt-[38px] flex flex-col items-center">
            <Image
              src="/logo.svg"
              alt="AItom"
              width={190}
              height={46}
              priority
              className="h-auto w-[170px] object-contain"
            />
            <p className="mt-[20px] text-[22px] text-coolgray-60">회원가입</p>
          </div>

          <form className="mt-[59px]" onSubmit={onSubmit}>
            <div className="space-y-5">
              <div>
                <label className="text-[16px] text-coolgray-60">아이디</label>
                <input
                  className="mt-2 w-full rounded-[8px] bg-coolgray-10 px-4 py-3 text-[16px] outline-none"
                  placeholder="아이디를 입력해주세요"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <label className="text-[16px] text-coolgray-60">비밀번호</label>
                <input
                  type="password"
                  className="mt-2 w-full rounded-[8px] bg-coolgray-10 px-4 py-3 text-[16px] outline-none"
                  placeholder="비밀번호를 입력해주세요"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div className="mt-[59px]">
              <button
                type="submit"
                disabled={loading}
                className="w-[474px] h-14 px-4 py-5 bg-slate-200 rounded-[47.09px]
                          shadow-[inset_-2.69px_-5.38px_15.47px_rgba(0,4,117,0.15),inset_4.04px_4.04px_9.5px_rgba(255,255,255,0.47)]
                          outline outline-[1.35px] outline-offset-[-1.35px]
                          inline-flex justify-center items-center
                          hover:brightness-[0.98] active:brightness-[0.96] transition
                          disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <span className="px-4 flex justify-center items-center gap-2.5 text-white text-lg font-semibold leading-4 tracking-wide">
                  {loading ? "회원가입 중..." : "회원가입"}
                </span>
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
