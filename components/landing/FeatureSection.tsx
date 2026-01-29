import Image from "next/image";

type Feature = {
  id: number;
  title: string;
  description: string;
  icon: string;
};

const features: Feature[] = [
  {
    id: 1,
    title: "AI 챗봇 합성법 제안",
    description:
      "화학식이나 구조 정보 입력 시 AI가 최적의 합성법을 실시간으로 제안합니다.",
    icon: "/1.svg",
  },
  {
    id: 2,
    title: "합성법 도감",
    description:
      "화학식이나 구조 정보 입력 시 AI가 최적의 합성법을 실시간으로 제안합니다.",
    icon: "/2.svg",
  },
  {
    id: 3,
    title: "팀 협업 기능",
    description:
      "화학식이나 구조 정보 입력 시 AI가 최적의 합성법을 실시간으로 제안합니다.",
    icon: "/3.svg",
  },
];

export default function FeatureSection() {
  return (
    <section aria-label="무기물 재료 합성 실험 솔루션" className="w-full">
      {/* 배경은 화면 전체 */}
      <div className="w-full bg-[linear-gradient(250deg,#F2F8F8_12.1%,#F2FCFF_48.17%,#E5F3F3_84.93%)] flex justify-center">
        {/* 피그마 캔버스는 1440 고정 + 중앙정렬 */}
        <div className="relative hidden h-[640px] w-[1440px] lg:block">
          <h2 className="absolute left-[312px] top-[97.92px] text-center text-3xl font-semibold leading-[48px] text-coolgray-80">
            무기물 재료 합성 실험을 위한 연구자 맞춤형 솔루션을 제안합니다.
          </h2>

          <div className="left-[80px] top-[243.42px] absolute inline-flex items-center justify-start gap-9">
            {features.map((feature) => (
              <article
                key={feature.id}
                className="w-[403px] h-[310px] px-[32px] py-[49px] bg-white rounded-2xl shadow-[0px_0px_20.2px_rgba(0,0,0,0.02)] inline-flex flex-col justify-start items-start gap-2.5"
              >
                <div className="flex flex-col justify-start items-start gap-4">
                  <div className="w-20 h-20 flex items-center justify-center rounded-full bg-white">
                    <Image
                      src={feature.icon}
                      alt={feature.title}
                      width={88}
                      height={88}
                      className="object-contain"
                    />
                  </div>

                  <div className="flex flex-col justify-start items-start gap-2">
                    <h3 className="self-stretch text-[26px] font-semibold leading-10 text-coolgray-60">
                      {feature.title}
                    </h3>

                    <p className="w-80 text-zinc-500 text-[20px] font-medium leading-8">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
        {/* lg 미만: 반응형 레이아웃 */}
        <div className="block w-full px-4 py-16 lg:hidden">
          <h2 className="mx-auto max-w-xl text-center text-xl font-semibold leading-relaxed text-coolgray-80 sm:text-2xl">
            무기물 재료 합성 실험을 위한 연구자 맞춤형 솔루션을 제안합니다.
          </h2>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2">
            {features.map((feature) => (
              <article
                key={feature.id}
                className="rounded-2xl bg-white p-8 shadow-figma-card"
              >
                <div className="w-20 h-20 flex items-center justify-center rounded-full bg-white">
                  <Image
                    src={feature.icon}
                    alt={feature.title}
                    width={68}
                    height={68}
                    className="object-contain"
                  />
                </div>

                <h3 className="mt-4 text-lg font-semibold text-coolgray-80">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-coolgray-60">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
