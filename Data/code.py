import requests
import json
import pandas as pd
import time
from typing import List, Dict, Optional
import os
from datetime import datetime

class ScienceDirectCollector:
    def __init__(self, api_key: str):
        """
        ScienceDirect API를 사용한 논문 수집기
        
        Args:
            api_key (str): 발급받은 API 키
        """
        self.api_key = api_key
        self.base_url = "https://api.elsevier.com/content"
        self.headers = {
            'X-ELS-APIKey': api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    def search_articles(self, query: str, journal: str = "Journal of Catalysis", 
                       start: int = 0, count: int = 25) -> Dict:
        """
        논문 검색 (메타데이터만)
        
        Args:
            query (str): 검색 키워드 (예: "battery catalysis synthesis")
            journal (str): 저널명
            start (int): 시작 인덱스
            count (int): 한 번에 가져올 논문 수 (최대 100)
            
        Returns:
            Dict: API 응답 데이터
        """
        search_url = f"{self.base_url}/search/sciencedirect"
        
        # 검색 쿼리 구성
        search_query = f'"{query}" AND SRCTITLE("{journal}")'
        
        params = {
            'query': search_query,
            'start': start,
            'count': count,
            'sort': 'date',  # 날짜순 정렬
            'field': 'doi,title,authors,publicationName,coverDate,abstract,uri'
        }
        
        try:
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"검색 중 오류 발생: {e}")
            return {}
    
    def get_full_text(self, pii: str) -> Optional[Dict]:
        """
        PII를 사용하여 전문 가져오기
        
        Args:
            pii (str): 논문의 PII (Publisher Item Identifier)
            
        Returns:
            Dict: 전문 데이터 또는 None
        """
        fulltext_url = f"{self.base_url}/article/pii/{pii}"
        
        params = {
            'view': 'FULL'  # 전문 요청
        }
        
        try:
            response = requests.get(fulltext_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"전문 가져오기 중 오류 발생 (PII: {pii}): {e}")
            return None
    
    def extract_pii_from_uri(self, uri: str) -> Optional[str]:
        """
        URI에서 PII 추출
        
        Args:
            uri (str): 논문 URI
            
        Returns:
            str: PII 또는 None
        """
        try:
            # URI 형식: https://api.elsevier.com/content/article/pii/S0021951720305090
            if '/pii/' in uri:
                return uri.split('/pii/')[-1]
            return None
        except:
            return None
    
    def collect_articles(self, query: str = "battery catalysis synthesis", 
                        max_articles: int = 10000) -> List[Dict]:
        """
        논문 대량 수집
        
        Args:
            query (str): 검색 키워드
            max_articles (int): 최대 수집할 논문 수
            
        Returns:
            List[Dict]: 수집된 논문 데이터 리스트
        """
        all_articles = []
        start = 0
        batch_size = 100  # 한 번에 가져올 논문 수 (최대 100)
        
        print(f"'{query}' 키워드로 논문 수집 시작...")
        
        while len(all_articles) < max_articles:
            print(f"진행상황: {len(all_articles)}/{max_articles} 논문 수집됨")
            
            # 검색 실행
            search_results = self.search_articles(
                query=query, 
                start=start, 
                count=min(batch_size, max_articles - len(all_articles))
            )
            
            if not search_results or 'search-results' not in search_results:
                print("더 이상 검색 결과가 없습니다.")
                break
                
            entries = search_results.get('search-results', {}).get('entry', [])
            
            if not entries:
                print("더 이상 논문이 없습니다.")
                break
            
            # 각 논문 처리
            for entry in entries:
                article_data = {
                    'title': entry.get('dc:title', ''),
                    'authors': self._extract_authors(entry),
                    'journal': entry.get('prism:publicationName', ''),
                    'date': entry.get('prism:coverDate', ''),
                    'doi': entry.get('prism:doi', ''),
                    'abstract': entry.get('dc:description', ''),
                    'uri': entry.get('prism:url', ''),
                    'pii': self.extract_pii_from_uri(entry.get('prism:url', ''))
                }
                
                all_articles.append(article_data)
                
                if len(all_articles) >= max_articles:
                    break
            
            start += batch_size
            
            # API 요청 제한을 위한 대기
            time.sleep(1)
        
        print(f"총 {len(all_articles)}개 논문 수집 완료!")
        return all_articles
    
    def collect_full_texts(self, articles: List[Dict], save_path: str = "full_texts") -> List[Dict]:
        """
        수집된 논문들의 전문 다운로드
        
        Args:
            articles (List[Dict]): 논문 메타데이터 리스트
            save_path (str): 전문을 저장할 폴더 경로
            
        Returns:
            List[Dict]: 전문이 포함된 논문 데이터
        """
        os.makedirs(save_path, exist_ok=True)
        
        articles_with_fulltext = []
        
        for i, article in enumerate(articles):
            print(f"전문 다운로드 진행: {i+1}/{len(articles)}")
            
            pii = article.get('pii')
            if not pii:
                print(f"PII 없음: {article.get('title', 'Unknown')}")
                continue
            
            # 전문 가져오기
            fulltext_data = self.get_full_text(pii)
            
            if fulltext_data:
                article['fulltext'] = fulltext_data
                
                # 개별 파일로 저장
                filename = f"{save_path}/article_{pii}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(article, f, ensure_ascii=False, indent=2)
                
                print(f"저장됨: {filename}")
            else:
                print(f"전문 다운로드 실패: {article.get('title', 'Unknown')}")
            
            articles_with_fulltext.append(article)
            
            # API 요청 제한을 위한 대기 (중요!)
            time.sleep(2)
        
        return articles_with_fulltext
    
    def _extract_authors(self, entry: Dict) -> str:
        """
        저자 정보 추출
        
        Args:
            entry (Dict): 논문 엔트리
            
        Returns:
            str: 저자 이름들
        """
        authors = entry.get('authors', {}).get('author', [])
        if isinstance(authors, list):
            return '; '.join([author.get('given-name', '') + ' ' + author.get('surname', '') 
                            for author in authors])
        elif isinstance(authors, dict):
            return authors.get('given-name', '') + ' ' + authors.get('surname', '')
        return ''
    
    def save_to_csv(self, articles: List[Dict], filename: str = "collected_articles.csv"):
        """
        수집된 데이터를 CSV로 저장
        
        Args:
            articles (List[Dict]): 논문 데이터
            filename (str): 저장할 파일명
        """
        # 전문 데이터는 제외하고 메타데이터만 CSV로 저장
        csv_data = []
        for article in articles:
            csv_row = {k: v for k, v in article.items() if k != 'fulltext'}
            csv_data.append(csv_row)
        
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"CSV 파일 저장됨: {filename}")

# 사용 예시
def main():
    # API 키 설정 (환경변수 또는 직접 입력)
    API_KEY = "cb5adb1eb4720ef153d4f8e1583925e2"  # 실제 키로 교체
    
    # 수집기 초기화
    collector = ScienceDirectCollector(API_KEY)
    
    # 1단계: 논문 메타데이터 수집
    print("=== 1단계: 논문 검색 및 메타데이터 수집 ===")
    articles = collector.collect_articles(
        query="battery catalysis synthesis",
        max_articles=100  # 테스트용으로 100개만
    )
    
    # 메타데이터를 CSV로 저장
    collector.save_to_csv(articles, "battery_catalysis_articles.csv")
    
    # 2단계: 전문 다운로드 (선택적)
    print("\n=== 2단계: 전문 다운로드 ===")
    # 주의: 전문 다운로드는 시간이 많이 걸리고 API 제한이 있을 수 있습니다
    
    # 처음 10개만 테스트
    test_articles = articles[:10]
    articles_with_fulltext = collector.collect_full_texts(
        test_articles, 
        save_path="full_texts"
    )
    
    print("수집 완료!")

if __name__ == "__main__":
    main()