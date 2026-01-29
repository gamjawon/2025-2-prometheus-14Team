// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ✅ 이제 text-coolgray-80, bg-coolgray-10 이런게 피그마 값으로 바로 먹음
        coolgray: {
          5: "rgb(var(--coolgray-05) / <alpha-value>)",
          10: "rgb(var(--coolgray-10) / <alpha-value>)",
          20: "rgb(var(--coolgray-20) / <alpha-value>)",
          30: "rgb(var(--coolgray-30) / <alpha-value>)",
          40: "rgb(var(--coolgray-40) / <alpha-value>)",
          60: "rgb(var(--coolgray-60) / <alpha-value>)",
          80: "rgb(var(--coolgray-80) / <alpha-value>)",
          90: "rgb(var(--coolgray-90) / <alpha-value>)",
        },
        blue: {
          DEFAULT: "rgb(var(--blue) / <alpha-value>)",
          10: "rgb(var(--blue-10) / <alpha-value>)",
          50: "rgb(var(--blue-50) / <alpha-value>)",
        },
        white: "rgb(var(--white) / <alpha-value>)",
      },

      // ✅ 그라데이션도 “이름”으로 등록해서 피그마랑 똑같이 씀
       backgroundImage: {
        "landing-gradient":
          "linear-gradient(180deg, rgb(var(--landing-grad-0)) 0%, rgb(var(--landing-grad-50)) 50%, rgb(var(--landing-grad-100)) 100%)",
      },

      // (선택) 그림자도 피그마 값으로 이름 붙이기
      boxShadow: {
        "figma-card": "0px 0px 20.2px rgba(0,0,0,0.05)",
      },
      fontFamily: {
        pretendard: ["var(--font-pretendard)"],
      },
    },
  },
  plugins: [],
};

export default config;
