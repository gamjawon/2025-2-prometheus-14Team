# collect_fulltext.py
import requests, json, time, argparse, os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

BASE_URL = "https://api.elsevier.com/content"

SEED_JOURNALS = [
    "Journal of Catalysis",
    "ACS Catalysis",
    "Applied Catalysis B: Environmental",
    "Applied Catalysis A: General",
    "Catalysis Today",
    "Catalysis Science & Technology",
    "ChemCatChem",
    "Chinese Journal of Catalysis",
    "Catalysis Communications",
    "Molecular Catalysis",
    "Journal of Energy Chemistry",
]

def make_headers(api_key: str, inst_token: Optional[str]) -> Dict[str, str]:
    h = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if inst_token:
        h["X-ELS-Insttoken"] = inst_token
    return h

def sd_search(api_key: str, inst_token: Optional[str], search_query: str, start: int=0, count: int=25) -> Optional[Dict]:
    """
    ScienceDirect 검색. 계정/엔드포인트 차이를 대비해 query/qs 두 방식 자동 폴백.
    """
    headers = make_headers(api_key, inst_token)
    url = f"{BASE_URL}/search/sciencedirect"
    attempts = [
        {"params": {"query": search_query, "start": start, "count": count}},
        {"params": {"qs": search_query, "offset": start, "count": count}},
    ]
    for attempt in attempts:
        try:
            r = requests.get(url, headers=headers, params=attempt["params"], timeout=30)
            if r.status_code == 200:
                data = r.json()
                entries = data.get("search-results", {}).get("entry", [])
                if entries and not (len(entries) == 1 and "error" in entries[0]):
                    return data
            elif r.status_code in (403, 429):
                # 권한/쿼터: 약한 백오프 후 다음 시도
                time.sleep(2)
        except requests.RequestException:
            pass
    return None

def get_total_results(api_key: str, inst_token: Optional[str], keyword: str, journal: Optional[str]=None) -> int:
    q = f'{keyword} AND SRCTITLE("{journal}")' if journal else keyword
    data = sd_search(api_key, inst_token, q, start=0, count=1)
    if not data:
        return 0
    return int(data.get("search-results", {}).get("opensearch:totalResults", "0"))

def discover_catalysis_journals(api_key: str, inst_token: Optional[str], sample_count: int=200) -> List[str]:
    """
    'catalysis'로 SD 검색 → publicationName 중 'catalysis' 포함 저널 추출 + 시드 합치기.
    """
    found = set(SEED_JOURNALS)
    data = sd_search(api_key, inst_token, "catalysis", start=0, count=sample_count)
    if data:
        entries = data.get("search-results", {}).get("entry", [])
        for e in entries:
            j = e.get("prism:publicationName", "")
            if j and "catalysis" in j.lower():
                found.add(j)
    return sorted(found)

def extract_pii_from_uri(uri: str) -> Optional[str]:
    if not uri:
        return None
    if "/pii/" in uri:
        return uri.split("/pii/")[-1] or None
    return None

def extract_authors(entry: Dict) -> str:
    a = entry.get("authors")
    if isinstance(a, dict) and "author" in a:
        authors = a["author"]
        if isinstance(authors, list):
            return "; ".join([
                f"{x.get('given-name','')} {x.get('surname','')}".strip()
                for x in authors if isinstance(x, dict)
            ])
        if isinstance(authors, dict):
            return f"{authors.get('given-name','')} {authors.get('surname','')}".strip()
    creator = entry.get("dc:creator")
    if isinstance(creator, str):
        return creator
    if isinstance(creator, list):
        return "; ".join([str(c) for c in creator])
    return ""

def get_full_text_json(api_key: str, inst_token: Optional[str], pii: str, max_retries: int=4) -> Optional[Dict]:
    """
    전문 JSON(FULL) 조회. 403/404/429 처리 + 지수 백오프.
    """
    headers = make_headers(api_key, inst_token)
    url = f"{BASE_URL}/article/pii/{pii}"
    params = {"view": "FULL"}
    delay = 1.5
    for attempt in range(1, max_retries+1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=45)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 404:
                # 없는 PII
                return None
            elif r.status_code in (403, 429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
            else:
                # 기타 에러
                time.sleep(delay)
                delay *= 1.5
        except requests.RequestException:
            time.sleep(delay)
            delay *= 2
    return None

def collect_from_journal(api_key: str, inst_token: Optional[str], keyword: str, journal: str, need: int,
                         out_dir: str, start_index: int=0, page_size: int=25,
                         seen: Optional[set]=None) -> Tuple[int, int]:
    """
    단일 저널에서 keyword로 need개까지 수집 + 전문 저장.
    반환: (저장 성공 개수, 다음 start 인덱스)
    """
    os.makedirs(out_dir, exist_ok=True)
    saved = 0
    start = start_index
    seen = seen or set()

    while saved < need:
        q = f'{keyword} AND SRCTITLE("{journal}")'
        data = sd_search(api_key, inst_token, q, start=start, count=min(page_size, need - saved))
        if not data:
            break
        entries = data.get("search-results", {}).get("entry", [])
        if not entries or (len(entries) == 1 and "error" in entries[0]):
            break

        for e in entries:
            if "error" in e:
                continue
            uri = e.get("prism:url", "")
            doi = e.get("prism:doi", "")
            pii = extract_pii_from_uri(uri)
            identifier = doi or pii or e.get("dc:title", "")
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)

            meta = {
                "title": e.get("dc:title", ""),
                "authors": extract_authors(e),
                "journal": e.get("prism:publicationName", ""),
                "date": e.get("prism:coverDate", ""),
                "doi": doi,
                "abstract": e.get("dc:description", ""),
                "uri": uri,
                "pii": pii,
            }

            if not pii:
                # PII 없으면 전문 접근 불가 → 스킵(요구사항: 무조건 전문 저장)
                continue

            full_json = get_full_text_json(api_key, inst_token, pii)
            if not full_json:
                # 접근 실패/권한/404 → 스킵
                continue

            # 저장 파일명: PII 기준
            safe_pii = "".join(c for c in pii if c.isalnum())
            out_path = os.path.join(out_dir, f"{safe_pii}.json")
            payload = {
                "metadata": meta,
                "fulltext": full_json
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            saved += 1

            if saved >= need:
                break

        start += page_size
        time.sleep(0.5)  # rate-limit 여유
    return saved, start

def save_csv(rows: List[Dict], path: str):
    df = pd.DataFrame([{k: v for k, v in r.items()} for r in rows])
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"💾 Saved: {path} ({len(rows)} rows)")

def load_existing_papers(out_dir: str) -> Tuple[set, int]:
    """
    기존 저장된 JSON 파일에서 PII/DOI 추출해서 seen 세트 구성 + 개수 카운트
    """
    seen = set()
    count = 0
    
    if not os.path.exists(out_dir):
        return seen, count
    
    for filename in os.listdir(out_dir):
        if not filename.endswith('.json') or filename == 'run_log.json':
            continue
        
        try:
            filepath = os.path.join(out_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                meta = data.get('metadata', {})
                
                # 식별자 추출 (collect_from_journal과 동일한 우선순위)
                doi = meta.get('doi', '')
                pii = meta.get('pii', '')
                title = meta.get('title', '')
                identifier = doi or pii or title
                
                if identifier:
                    seen.add(identifier)
                    count += 1
        except (json.JSONDecodeError, IOError):
            # 손상된 파일은 스킵
            continue
    
    return seen, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api_key", required=True, help="Elsevier API key")
    ap.add_argument("--inst_token", default=None, help="Institution token (optional, 권한 문제시 권장)")
    ap.add_argument("--keyword", default="catalyst")
    ap.add_argument("--target", type=int, default=10000)
    ap.add_argument("--page_size", type=int, default=25)
    ap.add_argument("--out_dir", default="sd_fulltexts", help="전문 JSON 저장 디렉토리")
    ap.add_argument("--dry_discover_only", action="store_true")
    args = ap.parse_args()

    # ===== 기존 파일 로드 추가 =====
    print("=== Step 0. 기존 저장된 논문 확인 ===")
    seen, saved_total = load_existing_papers(args.out_dir)
    print(f"기존 저장된 논문: {saved_total}개")
    print(f"중복 체크용 식별자: {len(seen)}개")
    
    if saved_total >= args.target:
        print(f"✅ 이미 목표({args.target})를 달성했습니다. 종료.")
        return
    
    need = args.target - saved_total
    print(f"추가로 수집할 논문: {need}개\n")
    # ================================

    print("=== Step 1. 관련 저널 자동 탐색 ===")
    journals = discover_catalysis_journals(args.api_key, args.inst_token)
    print(f"발견/시드 저널 수: {len(journals)}")
    for j in journals:
        print(" -", j)

    print("\n=== Step 2. 저널별 'catalysis' 가능 편수 집계 ===")
    counts = []
    total_available = 0
    for j in journals:
        cnt = get_total_results(args.api_key, args.inst_token, args.keyword, j)
        counts.append((j, cnt))
        total_available += cnt
        print(f"{j}: {cnt}")
    counts.sort(key=lambda x: x[1], reverse=True)
    print(f"\n총 가능 편수: {total_available}")

    if args.dry_discover_only:
        print("탐색 전용 모드 종료.")
        return

    if total_available <= 0:
        print("수집 가능한 결과가 없습니다. 종료.")
        return

    os.makedirs(args.out_dir, exist_ok=True)
    meta_rows: List[Dict] = []

    print("\n=== Step 3. 수집(전문 저장) 시작 ===")
    for j, cnt in counts:
        if need <= 0 or cnt == 0:
            continue
        
        to_aim = min(cnt, need * 2)
        print(f"\n[{j}] 시도 목표(메타 조회): {to_aim} / 남은 전문 저장 필요: {need}")

        saved_now, _ = collect_from_journal(
            api_key=args.api_key,
            inst_token=args.inst_token,
            keyword=args.keyword,
            journal=j,
            need=min(need, to_aim),
            out_dir=args.out_dir,
            start_index=0,
            page_size=args.page_size,
            seen=seen  # 기존 파일에서 로드한 seen 사용
        )
        saved_total += saved_now
        need -= saved_now
        print(f"  → 전문 저장 성공: {saved_now}개 (누적 {saved_total})")

        if saved_total >= args.target:
            break
        time.sleep(1.0)

    print(f"\n최종 전문 저장 개수: {saved_total} / 목표 {args.target}")
    if saved_total < args.target:
        print("⚠️ 기관 권한/제한으로 전문 저장이 목표에 미달했습니다. 캠퍼스 네트워크/프록시 또는 Insttoken 사용을 권장합니다.")

    log = {
        "timestamp": datetime.now().isoformat(),
        "keyword": args.keyword,
        "target": args.target,
        "saved_fulltexts": saved_total,
        "out_dir": args.out_dir,
        "journals_tried": [j for j, _ in counts]
    }
    with open(os.path.join(args.out_dir, "run_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print("완료!")

if __name__ == "__main__":
    main()
