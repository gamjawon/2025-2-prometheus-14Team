import { NextResponse } from "next/server";


export async function POST(req: Request) {
  // ✅ 1️⃣ 프론트에서 보낸 메시지 읽기
  const body = await req.json();
  const userMessage = body.message as string;

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      // (선택) 일반 응답 먼저
      controller.enqueue(
        encoder.encode("응답을 시작합니다.\n")
      );

      // ✅ 2️⃣ 여기서 조건 체크 + SAFETY_CHECK 전송
      if (userMessage.includes("합성")) {
        controller.enqueue(
          encoder.encode("[SAFETY_CHECK]")
        );
      }

      // (선택) 나머지 응답
      controller.enqueue(
        encoder.encode(
          "\nTiO2 나노입자 sol-gel 합성은 다음과 같이 진행됩니다."
        )
      );

      controller.close();
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache",
    },
  });
}

function delay(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}
