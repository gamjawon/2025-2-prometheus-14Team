"""
CAS number를 화학식(formula)으로 변환하는 유틸리티 모듈

PubChem REST API를 사용하여 CAS number로부터 화학식을 조회합니다.
"""

import os
import json
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# 로컬 캐시 파일 경로
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'cas_cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'cas_to_formula.json')


def _ensure_cache_dir():
    """캐시 디렉토리가 없으면 생성"""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_cache() -> dict:
    """캐시 파일에서 CAS -> formula 매핑 로드"""
    _ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(cache: dict):
    """캐시 파일에 CAS -> formula 매핑 저장"""
    _ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except IOError:
        pass  # 캐시 저장 실패해도 계속 진행


def _query_pubchem_api(cas_number: str) -> Optional[str]:
    """
    PubChem REST API를 사용하여 CAS number로부터 화학식 조회
    
    Parameters
    ----------
    cas_number : str
        CAS number (예: "471-34-1")
    
    Returns
    -------
    str or None
        화학식 문자열 (예: "CaCO3") 또는 None
    """
    # CAS number 정규화 (공백 제거, 하이픈 유지)
    cas_number = cas_number.strip().replace(' ', '')
    
    # PubChem REST API 엔드포인트
    # CAS number로 CID 조회
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    # Retry 전략 설정
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    
    try:
        # 1단계: CAS number로 CID 조회
        search_url = f"{base_url}/compound/name/{cas_number}/cids/JSON"
        response = session.get(search_url, timeout=10)
        
        if response.status_code != 200:
            # CAS number 직접 검색이 실패하면 property로 검색 시도
            search_url = f"{base_url}/compound/name/{cas_number}/property/MolecularFormula/JSON"
            response = session.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                    props = data['PropertyTable']['Properties']
                    if props and len(props) > 0:
                        formula = props[0].get('MolecularFormula')
                        if formula:
                            return formula
            return None
        
        data = response.json()
        if 'IdentifierList' not in data or 'CID' not in data['IdentifierList']:
            return None
        
        cids = data['IdentifierList']['CID']
        if not cids:
            return None
        
        # 첫 번째 CID 사용
        cid = cids[0]
        
        # 2단계: CID로부터 화학식 조회
        property_url = f"{base_url}/compound/cid/{cid}/property/MolecularFormula/JSON"
        response = session.get(property_url, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if 'PropertyTable' not in data or 'Properties' not in data['PropertyTable']:
            return None
        
        properties = data['PropertyTable']['Properties']
        if not properties or len(properties) == 0:
            return None
        
        formula = properties[0].get('MolecularFormula')
        return formula if formula else None
        
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        # 네트워크 오류나 파싱 오류 시 None 반환
        return None
    finally:
        session.close()


def cas_to_formula(cas_number: str, use_cache: bool = True) -> Optional[str]:
    """
    CAS number를 화학식(formula)으로 변환
    
    Parameters
    ----------
    cas_number : str
        CAS number (예: "471-34-1", "471341", "471 34 1")
    use_cache : bool, optional
        로컬 캐시 사용 여부 (기본값: True)
    
    Returns
    -------
    str or None
        화학식 문자열 (예: "CaCO3") 또는 None (찾을 수 없는 경우)
    
    Examples
    --------
    >>> cas_to_formula("471-34-1")
    'CaCO3'
    >>> cas_to_formula("123-45-6")
    None  # 존재하지 않는 CAS number
    """
    if not cas_number or not isinstance(cas_number, str):
        return None
    
    cas_number = cas_number.strip()
    if not cas_number:
        return None
    
    # 캐시 확인
    if use_cache:
        cache = _load_cache()
        if cas_number in cache:
            return cache[cas_number]
    
    # PubChem API 조회
    formula = _query_pubchem_api(cas_number)
    
    # 캐시에 저장 (None도 저장하여 재조회 방지)
    if use_cache:
        cache = _load_cache()
        cache[cas_number] = formula
        _save_cache(cache)
    
    return formula


if __name__ == '__main__':
    # 테스트 예제
    test_cases = [
        "471-34-1",  # CaCO3
        "1314-13-2",  # ZnO
        "1344-28-1",  # Al2O3
        "123-45-6",  # 존재하지 않는 CAS (None 반환 예상)
    ]
    
    print("CAS number -> Formula 변환 테스트:")
    print("-" * 50)
    for cas in test_cases:
        formula = cas_to_formula(cas)
        status = formula if formula else "None (찾을 수 없음)"
        print(f"{cas:15s} -> {status}")

