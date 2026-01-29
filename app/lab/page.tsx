import AppShell from "@/components/layout/AppShell";
import RecipeCard from "@/components/lab/RecipeCard";

export default function Page() {
  return (
    <AppShell>
      <div className="p-8">
        <div className="mx-auto w-full max-w-[1100px]">
          {/* 여기서 스샷처럼 상단 프로젝트 카드/팀원/정렬/추가 버튼 구성 */}
          <div className="grid grid-cols-2 gap-4">
            <RecipeCard />
            <RecipeCard />
            <RecipeCard />
            <RecipeCard />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
