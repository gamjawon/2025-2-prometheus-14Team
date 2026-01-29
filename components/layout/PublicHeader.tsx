import Image from "next/image";
import Link from "next/link";
import Button from "@/components/ui/Button";

type Props = {
  hideAuthButtons?: boolean;
};

export default function PublicHeader({ hideAuthButtons = false }: Props) {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="flex items-center justify-between px-5 py-3 lg:px-[80px] lg:py-[16px]">
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.svg"
            alt="AItom"
            width={107}
            height={26}
            priority
            className="h-auto w-[84px] lg:w-[107px]"
          />
        </Link>

        <div
        className={`flex items-center gap-[12px] ${
          hideAuthButtons ? "opacity-0 pointer-events-none" : ""
        }`}
      >
          <Link href="/login">
            <Button
              variant="ghost"
              className="
                h-[48px]
                rounded-[30px]
                bg-coolgray-10
                border-0
                px-[28px]
                py-[16px]
                text-base
                text-coolgray-80
              "
     >
              로그인
            </Button>
          </Link>
          <Link href="/chat">
            <Button
              variant="gradient"
              className="h-[48px] rounded-[30px] px-[32px] py-[16px] text-base"
            >
              시작하기
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
