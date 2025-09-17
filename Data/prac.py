import requests
import json
from pprint import pprint

def test_sciencedirect_api(api_key):
    """
    ScienceDirect API 테스트 - 논문 1개만 추출
    """
    print("=== ScienceDirect API 테스트 시작 ===\n")
    
    # API 설정
    headers = {
        'X-ELS-APIKey': api_key,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # 1단계: 논문 검색 (1개만)
    print("1단계: 논문 검색 중...")
    search_url = "https://api.elsevier.com/content/search/sciencedirect"
    
    search_params = {
        'query': 'battery catalysis AND SRCTITLE("Journal of Catalysis")',
        'count': 1,  # 1개만 가져오기
        'field': 'doi,title,authors,publicationName,coverDate,abstract,uri'
    }
    
    try:
        search_response = requests.get(search_url, headers=headers, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        print("✅ 검색 성공!")
        
        # 검색 결과 확인
        entries = search_data.get('search-results', {}).get('entry', [])
        
        if not entries:
            print("❌ 검색 결과가 없습니다.")
            return
        
        # 첫 번째 논문 정보 출력
        article = entries[0]
        print("\n=== 찾은 논문 정보 ===")
        print(f"제목: {article.get('dc:title', 'N/A')}")
        print(f"저널: {article.get('prism:publicationName', 'N/A')}")
        print(f"날짜: {article.get('prism:coverDate', 'N/A')}")
        print(f"DOI: {article.get('prism:doi', 'N/A')}")
        print(f"URI: {article.get('prism:url', 'N/A')}")
        
        # 초록이 있으면 출력 (일부만)
        abstract = article.get('dc:description', '')
        if abstract:
            print(f"초록 (일부): {abstract[:200]}...")
        
        # 2단계: 전문 가져오기 시도
        print("\n2단계: 전문 가져오기 시도...")
        
        # URI에서 PII 추출
        uri = article.get('prism:url', '')
        if '/pii/' in uri:
            pii = uri.split('/pii/')[-1]
            print(f"PII: {pii}")
            
            # 전문 API 호출
            fulltext_url = f"https://api.elsevier.com/content/article/pii/{pii}"
            fulltext_params = {'view': 'FULL'}
            
            try:
                fulltext_response = requests.get(fulltext_url, headers=headers, params=fulltext_params)
                
                if fulltext_response.status_code == 200:
                    print("✅ 전문 접근 성공!")
                    fulltext_data = fulltext_response.json()
                    
                    # 전문 데이터 구조 확인
                    print("\n=== 전문 데이터 구조 ===")
                    print("사용 가능한 키들:", list(fulltext_data.keys()))
                    
                    # 논문 내용 일부 출력
                    if 'full-text-retrieval-response' in fulltext_data:
                        ft_response = fulltext_data['full-text-retrieval-response']
                        print("전문 응답 키들:", list(ft_response.keys()))
                        
                        # 실제 내용 확인
                        if 'originalText' in ft_response:
                            text = ft_response['originalText']
                            print(f"원문 일부: {str(text)[:300]}...")
                        
                    # 결과를 파일로 저장
                    with open('test_article_fulltext.json', 'w', encoding='utf-8') as f:
                        json.dump(fulltext_data, f, ensure_ascii=False, indent=2)
                    print("\n📁 전문 데이터가 'test_article_fulltext.json'에 저장되었습니다.")
                    
                elif fulltext_response.status_code == 403:
                    print("❌ 전문 접근 권한 없음 (403 Forbidden)")
                    print("   - API 키가 아직 활성화되지 않았을 수 있습니다.")
                    print("   - 또는 해당 논문에 대한 기관 구독이 없을 수 있습니다.")
                    
                elif fulltext_response.status_code == 404:
                    print("❌ 논문을 찾을 수 없음 (404 Not Found)")
                    
                else:
                    print(f"❌ 전문 가져오기 실패: {fulltext_response.status_code}")
                    print(f"응답: {fulltext_response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 전문 요청 중 오류: {e}")
        else:
            print("❌ URI에서 PII를 찾을 수 없습니다.")
        
        # 메타데이터를 파일로 저장
        with open('test_article_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        print("\n📁 메타데이터가 'test_article_metadata.json'에 저장되었습니다.")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 검색 요청 중 오류 발생: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"응답 코드: {e.response.status_code}")
            print(f"응답 내용: {e.response.text}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def test_api_key_validity(api_key):
    """
    API 키 유효성 간단 테스트
    """
    print("=== API 키 유효성 테스트 ===")
    
    headers = {
        'X-ELS-APIKey': api_key,
        'Accept': 'application/json'
    }
    
    # 간단한 검색으로 API 키 테스트
    test_url = "https://api.elsevier.com/content/search/sciencedirect"
    test_params = {'query': 'test', 'count': 1}
    
    try:
        response = requests.get(test_url, headers=headers, params=test_params)
        
        if response.status_code == 200:
            print("✅ API 키가 유효합니다!")
            return True
        elif response.status_code == 401:
            print("❌ API 키가 유효하지 않거나 만료되었습니다.")
            return False
        elif response.status_code == 403:
            print("⚠️  API 키는 유효하지만 권한이 제한적입니다.")
            print("   (아직 활성화되지 않았을 수 있습니다)")
            return True
        else:
            print(f"❌ 예상치 못한 응답: {response.status_code}")
            print(f"응답 내용: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 중 오류: {e}")
        return False

# 실행 함수
def main():
    # 여기에 실제 API 키를 입력하세요
    API_KEY = "cb5adb1eb4720ef153d4f8e1583925e2"  # 실제 키로 교체
    
    print("🔬 ScienceDirect API 테스트 도구\n")
    
    # 1. API 키 유효성 테스트
    if not test_api_key_validity(API_KEY):
        print("\n❌ API 키 문제로 테스트를 중단합니다.")
        return
    
    print("\n" + "="*50 + "\n")
    
    # 2. 실제 논문 검색 및 전문 가져오기 테스트
    test_sciencedirect_api(API_KEY)
    
    print("\n" + "="*50)
    print("🎉 테스트 완료!")
    print("\n생성된 파일들:")
    print("- test_article_metadata.json: 논문 메타데이터")
    print("- test_article_fulltext.json: 논문 전문 (성공 시)")

if __name__ == "__main__":
    main()