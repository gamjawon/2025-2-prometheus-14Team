import { apiFetch } from "@/lib/api";

// ✅ 스웨거에서 확인된 회원가입
export async function register(payload: { username: string; password: string }) {
  return apiFetch("/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * ✅ 로그인 (엔드포인트/응답 키는 백엔드에 따라 다를 수 있음)
 * - 보통: POST /login 또는 /token 또는 /auth/login
 * - 응답: { access_token: "...", token_type: "bearer" } 형태가 흔함
 */
export async function login(payload: { username: string; password: string }) {
  // 1) 아래 경로가 너희 백엔드랑 다르면 /docs에서 로그인 경로로 바꿔줘
  const data: any = await apiFetch("/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  // 2) 토큰 키 이름도 백엔드마다 달라서 최대한 호환되게 처리
  const token =
    data?.access_token ||
    data?.token ||
    data?.jwt ||
    data?.accessToken;

  if (!token) {
    throw new Error("로그인 응답에 토큰(access_token/token)이 없습니다. (/docs에서 응답 형식 확인 필요)");
  }

  localStorage.setItem("access_token", token);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
}
