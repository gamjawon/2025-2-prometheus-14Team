import PublicHeader from "@/components/layout/PublicHeader";
import Link from "next/link";
import Button from "@/components/ui/Button";
import FeatureSection from "@/components/landing/FeatureSection";
import Image from "next/image";

export default function Page() {
  return (
    <div className="min-h-dvh bg-white">
      <PublicHeader />


      <section className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-8 pt-[74px] pb-[120px]">

        <div className="flex flex-col items-center text-center gap-[18px]">
          {/* 심볼 + 그림자 (18px 간격) */}
          <div className="flex flex-col items-center gap-[18px]">
            <Image
              src="/symbol.svg"
              alt="AItom Symbol"
              width={205}
              height={202}
              priority
              className="w-[205px] h-auto"
            />
            <Image
              src="/symbol-shadow.svg"
              alt=""
              width={172}
              height={18}
              className="w-[172px] h-auto"
            />
          </div>

          {/* 원래 text-6xl 타이틀 자리에 로고를 두되 과하지 않게 */}
          <Image
            src="/logo_black.svg"
            alt="AItom"
            width={274}
            height={67}
            className="mt-[36px] w-[274px] h-auto"
          />

        
          <p className="mt-[30px] text-[24px] leading-[32px] text-coolgray-60">
            화학식을 바탕으로 최적의 합성법을 제안하는 AI챗봇
          </p>

          <Link href="/chat" className="mt-10">
            <Button variant="gradient" className="text-[24px] px-[62px] py-[22px] rounded-[47px]">
              시작하기
            </Button>
          </Link>

        </div>
      </section>

  
          <FeatureSection />
          <div className="h-[203px]" />
        
    </div>  
  );
}
