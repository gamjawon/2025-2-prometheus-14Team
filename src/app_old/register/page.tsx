"use client";

import { useState } from "react";
import { register } from "../../../services/auth";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await register({ username, password });
      alert(result.message); // "Registration successful"
      router.push("/login"); // 로그인 페이지로 이동 (있다면)
    } catch (err: any) {
      alert(err?.message ?? "에러");
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 max-w-sm">
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="username"
        className="border p-2 rounded"
      />
      <input
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="password"
        type="password"
        className="border p-2 rounded"
      />
      <button className="border p-2 rounded" type="submit">
        회원가입
      </button>
    </form>
  );
}
