"""
Chemical Synthesis GraphRAG System 
타겟 물질별 합성법 쿼리 지원
"""
from __future__ import annotations
from rdflib import Graph, Namespace, RDF, RDFS
from typing import List, Dict, Optional, Set
from collections import defaultdict
import re
from typing import Iterable

class ChemicalKnowledgeGraph:
    """RDF 지식 그래프 관리 클래스 (개선 버전)"""
    
    def __init__(self, rdf_file: str):
        """
        Args:
            rdf_file: RDF 파일 경로
        """
        self.graph = Graph()
        self.graph.parse(rdf_file, format="xml")
        
        # 네임스페이스 정의
        self.AITON = Namespace("http://www.aitom.com/aiton.owl#")
        self.RDF = RDF
        self.RDFS = RDFS
        
        print(f"✓ RDF 파일 로드 완료")
        print(f"  - 총 트리플 수: {len(self.graph)}")
        self._print_statistics()
    
    def _print_statistics(self):
        """그래프 통계 출력"""
        # 물질(InorganicMaterial) 수
        materials = list(self.graph.subjects(predicate=self.RDF.type, 
                                            object=self.AITON.InorganicMaterial))
        print(f"  - 무기 물질: {len(materials)}개")
        
        # 합성법(SynthesisMethod) 수
        methods = list(self.graph.subjects(predicate=self.RDF.type,
                                          object=self.AITON.SynthesisMethod))
        print(f"  - 합성 방법: {len(methods)}개")
        
        # 합성 단계 수
        steps = list(self.graph.subjects(predicate=self.RDF.type, 
                                        object=self.AITON.SynthesisStep))
        print(f"  - 합성 단계: {len(steps)}개")
    
    def list_all_materials(self) -> List[str]:
        query = """
        PREFIX aiton: <http://www.aitom.com/aiton.owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT DISTINCT ?materialLabel
        WHERE {
            ?material rdf:type aiton:InorganicMaterial .
            ?material rdfs:label ?materialLabel .
        }
        ORDER BY ?materialLabel
        """
        results = list(self.graph.query(query))
        return [str(row.materialLabel) for row in results]

    
    def query_all_synthesis_by_target(self, target_material: str) -> Optional[List[Dict]]:
        print(f"\n[DEBUG] GraphDB 쿼리: 타겟 물질 = '{target_material}'")
        print("-" * 80)

        material_uri = self._find_material_uri(target_material)
        if not material_uri:
            print(f"❌ 물질 '{target_material}'을(를) 찾을 수 없습니다.")
            return None
        print(f"✓ 물질 URI 발견: {material_uri}")

        # ✅ 여러 method 전부 가져오기
        method_uris = list(self.graph.objects(material_uri, self.AITON.hasSynthesisMethod))
        if not method_uris:
            print(f"❌ '{target_material}'의 합성법이 없습니다.")
            return None
        print(f"✓ 합성법 URI {len(method_uris)}개 발견")

        all_methods: List[Dict] = []

        for mi, method_uri in enumerate(method_uris, 1):
            method_label = self.graph.value(method_uri, self.RDFS.label)
            method_label = str(method_label) if method_label else f"method_{mi}"

            # ✅ 어떤 RDF는 consistOfStep이 여러 개일 수 있음 (시작 step 후보)
            first_steps = list(self.graph.objects(method_uri, self.AITON.consistOfStep))
            if not first_steps:
                # method가 있지만 step이 없는 케이스는 스킵/기록
                all_methods.append({
                    "method_uri": str(method_uri),
                    "method_label": method_label,
                    "sequence": [],
                    "note": "no consistOfStep"
                })
                continue

            # 시작점이 여러 개면: (1) 각각 시퀀스로 뽑아두거나 (2) LLM 선택 대상으로 분기 가능
            # 여기서는 일단 각각을 별도 variant로 저장(권장)
            for si, first_step in enumerate(first_steps, 1):
                seq = self._walk_step_sequence(first_step)

                all_methods.append({
                    "method_uri": str(method_uri),
                    "method_label": method_label if len(first_steps) == 1 else f"{method_label} (start#{si})",
                    "first_step_uri": str(first_step),
                    "sequence": seq
                })

        print(f"✓ 총 {len(all_methods)}개 method-variant 추출 완료")
        print("-" * 80 + "\n")
        return all_methods


    def _walk_step_sequence(self, first_step_uri, max_steps: int = 50) -> List[Dict]:
        sequence = []
        current_step = first_step_uri
        step_num = 1
        visited = set()

        while current_step and step_num <= max_steps:
            if current_step in visited:
                # ✅ cycle 방지
                break
            visited.add(current_step)

            step_info = self._extract_step_info(current_step, step_num)
            if step_info:
                sequence.append(step_info)

            current_step = self.graph.value(current_step, self.AITON.nextStep)
            step_num += 1

        return sequence

    
    def _find_material_uri(self, material_name: str):
        """물질명으로 URI 찾기"""
        # 대소문자 무시 검색
        query = f"""
        PREFIX aiton: <http://www.aitom.com/aiton.owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?material
        WHERE {{
            ?material rdf:type aiton:InorganicMaterial .
            ?material rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{material_name}"))
        }}
        LIMIT 1
        """
        results = list(self.graph.query(query))
        return results[0].material if results else None
    
    def _extract_step_info(self, step_uri, step_num: int) -> Dict:
        labels = [str(o) for o in self.graph.objects(step_uri, self.RDFS.label)]
        if not labels:
            return None

        # "step_step_1. " 같은 접두 제거 후 키워드만 추출
        verbs = []
        for lb in labels:
            v = re.sub(r"^step_step_\d+\.\s*", "", lb).strip()
            if v:
                verbs.append(v.lower())

        # 중복 제거(순서 유지)
        seen = set()
        verbs_unique = [v for v in verbs if not (v in seen or seen.add(v))]

        info = {
            "step_number": step_num,
            "action": ", ".join(verbs_unique[:6]),  # 너무 길면 앞 6개만
            "precursor": None,
            "solvent": None,
            "condition": None
        }

        # 전구체/용매: 현재 RDF에 없을 가능성이 높음(추후 predicate 찾아서 추가해야 함)
        precursor = self.graph.value(step_uri, self.AITON.usesPrecursor)
        if precursor:
            prec_label = self.graph.value(precursor, self.RDFS.label)
            info["precursor"] = str(prec_label) if prec_label else None

        solvent = self.graph.value(step_uri, self.AITON.usesSolvent)
        if solvent:
            solv_label = self.graph.value(solvent, self.RDFS.label)
            info["solvent"] = str(solv_label) if solv_label else None

        condition = self.graph.value(step_uri, self.AITON.performedUnder)
        if condition:
            temp = self.graph.value(condition, self.AITON.hasTemperature)
            duration = self.graph.value(condition, self.AITON.hasDuration)
            if temp or duration:
                info["condition"] = {
                    "temperature": str(temp) if temp else None,
                    "duration": str(duration) if duration else None
                }

        return info

    
    def find_steps_with_precursor(self, precursor_name: str) -> List[Dict]:
        """특정 전구체를 사용하는 단계 찾기"""
        query = f"""
        PREFIX aiton: <http://www.aitom.com/aiton.owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?step ?stepLabel ?precursorLabel
        WHERE {{
            ?step aiton:usesPrecursor ?precursor .
            ?step rdfs:label ?stepLabel .
            ?precursor rdfs:label ?precursorLabel .
            FILTER(CONTAINS(LCASE(STR(?precursorLabel)), LCASE("{precursor_name}")))
        }}
        """
        results = list(self.graph.query(query))
        
        steps = []
        for row in results:
            steps.append({
                "step": str(row.stepLabel),
                "precursor": str(row.precursorLabel)
            })
        
        return steps
    
    def find_steps_with_solvent(self, solvent_name: str) -> List[Dict]:
        """특정 용매를 사용하는 단계 찾기"""
        query = f"""
        PREFIX aiton: <http://www.aitom.com/aiton.owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?step ?stepLabel ?solventLabel
        WHERE {{
            ?step aiton:usesSolvent ?solvent .
            ?step rdfs:label ?stepLabel .
            ?solvent rdfs:label ?solventLabel .
            FILTER(CONTAINS(LCASE(STR(?solventLabel)), LCASE("{solvent_name}")))
        }}
        """
        results = list(self.graph.query(query))
        
        steps = []
        for row in results:
            steps.append({
                "step": str(row.stepLabel),
                "solvent": str(row.solventLabel)
            })
        
        return steps
    
    def debug_triples_raw(self, uri, limit: int = 200):
        print("\n[DEBUG] RAW triples (including labels, all namespaces):")
        for i, (p, o) in enumerate(self.graph.predicate_objects(uri)):
            if i >= limit:
                print("  ... (truncated)")
                break
            print(f"  - {p} -> {o}")

    def debug_triples_compact(self, uri, limit: int = 200, include_label: bool = False):
        print("\n[DEBUG] COMPACT triples:")
        for i, (p, o) in enumerate(self.graph.predicate_objects(uri)):
            if i >= limit:
                print("  ... (truncated)")
                break

            if (not include_label) and str(p) == str(self.RDFS.label):
                continue

            # aiton predicate 또는 rdf:type는 출력
            if str(p).startswith(str(self.AITON)) or str(p) in (str(RDF.type), str(self.RDFS.label)):
                print(f"  - {p} -> {o}")

    def debug_target_links(self, target_material: str, max_print: int = 10):
        material_uri = self._find_material_uri(target_material)
        print("\n[DEBUG] material_uri:", material_uri)
        if not material_uri:
            return
        
        methods = list(self.graph.objects(material_uri, self.AITON.hasSynthesisMethod))
        print(f"[DEBUG] hasSynthesisMethod count = {len(methods)}")
        for m in methods[:max_print]:
            print("  method:", m)
            steps = list(self.graph.objects(m, self.AITON.consistOfStep))
            print(f"    consistOfStep count = {len(steps)}")
            for s in steps[:max_print]:
                lbl = self.graph.value(s, self.RDFS.label)
                print("      step:", s, "| label:", lbl)
            nxt = list(self.graph.objects(steps[0], self.AITON.nextStep)) if steps else []
            print("    nextStep from first step:", nxt[:max_print])




class TextConverter:
    """RDF 데이터를 자연어로 변환하는 클래스"""
    
    @staticmethod
    def sequence_to_text(sequence: List[Dict], material_name: str = "") -> str:
        """합성 순서를 자연어로 변환"""
        title = f"=== {material_name} 합성 절차 ===" if material_name else "=== 합성 절차 ==="
        text_lines = [title + "\n"]
        
        for step_info in sequence:
            step_num = step_info["step_number"]
            action = step_info["action"]
            
            line = f"Step {step_num}: {action}"
            
            # 전구체 정보
            if step_info["precursor"]:
                line += f"\n  └─ 전구체: {step_info['precursor']}"
            
            # 용매 정보
            if step_info["solvent"]:
                line += f"\n  └─ 용매: {step_info['solvent']}"
            
            # 조건 정보
            if step_info["condition"]:
                cond = step_info["condition"]
                if cond["temperature"]:
                    line += f"\n  └─ 온도: {cond['temperature']}°C"
                if cond["duration"]:
                    duration = cond["duration"].replace("PT", "").replace("H", "시간")
                    line += f"\n  └─ 시간: {duration}"
            
            text_lines.append(line)
        
        return "\n\n".join(text_lines)


class SynthesisRAG:
    """GraphRAG 메인 시스템 (개선 버전)"""
    
    def __init__(self, rdf_file: str):
        """
        Args:
            rdf_file: RDF 파일 경로
        """
        self.kg = ChemicalKnowledgeGraph(rdf_file)
        self.converter = TextConverter()
        
        # 사용 가능한 물질 목록 로드
        print("\n사용 가능한 물질 목록 로드 중...")
        self.available_materials = self.kg.list_all_materials()
        print(f"✓ 총 {len(self.available_materials)}개 물질")
        if len(self.available_materials) <= 20:
            print(f"  물질 목록: {', '.join(self.available_materials)}")
        print()
    
    def answer_question(self, question: str) -> Dict:
        """질문에 답변"""
        question_lower = question.lower()
        
        print(f"\n{'='*80}")
        print(f"[질문 분석] '{question}'")
        print(f"{'='*80}")
        
        # 1. 질문에서 타겟 물질 추출
        target_material = self._extract_target_material(question)
        
        if not target_material:
            return {
                "answer": "질문에서 타겟 물질을 찾을 수 없습니다. 물질명을 명확히 입력해주세요.",
                "context": [],
                "confidence": "none",
                "available_materials": self.available_materials[:20]  # 최대 20개
            }
        
        print(f"\n✓ 타겟 물질 인식: '{target_material}'")
        
        # 2. GraphDB에서 해당 물질의 합성법 쿼리
        methods = self.kg.query_all_synthesis_by_target(target_material)
        
        if not methods:
            return {
                "answer": f"'{target_material}'의 합성법을 찾을 수 없습니다.",
                "context": [],
                "confidence": "none",
                "available_materials": self.available_materials[:20]
            }
        
        # 3. 컨텍스트 생성
        context_text = self.converter.sequence_to_text(methods, target_material)
        
        # 4. 답변 생성
        answer = self._generate_answer(question, context_text, target_material)
        
        return {
            "answer": answer,
            "context": [context_text],
            "confidence": "high",
            "target_material": target_material
        }
    
    def _extract_target_material(self, question: str) -> Optional[str]:
        """질문에서 타겟 물질 추출"""
        question_lower = question.lower()
        
        # 사용 가능한 물질 목록에서 매칭
        for material in self.available_materials:
            material_lower = material.lower()
            
            # 정확한 매칭
            if material_lower in question_lower:
                return material
            
            # 공백 제거 후 매칭
            material_no_space = material_lower.replace(" ", "")
            question_no_space = question_lower.replace(" ", "")
            if material_no_space in question_no_space:
                return material
        
        return None
    
    def _generate_answer(self, question: str, context: str, material: str) -> str:
        """컨텍스트 기반으로 답변 생성 (LLM 없이)"""
        answer_parts = [
            f"'{material}'의 합성법 정보입니다:\n",
            context
        ]
        
        return "\n".join(answer_parts)
    
    def interactive_mode(self):
        """대화형 모드"""
        print("=" * 80)
        print("Chemical Synthesis GraphRAG System (개선 버전)")
        print("=" * 80)
        print("\n명령어:")
        print("  - 질문 입력: '[물질명] 합성법 알려줘' 형식으로 질문하세요")
        print("  - 'list': 사용 가능한 물질 목록 보기")
        print("  - 'quit' 또는 'exit': 종료")
        print("  - 'help': 예시 질문 보기")
        print("\n" + "=" * 80 + "\n")
        
        while True:
            try:
                question = input("\n질문 > ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ['quit', 'exit', '종료']:
                    print("\n시스템을 종료합니다.")
                    break
                
                if question.lower() == 'list':
                    self._show_material_list()
                    continue
                
                if question.lower() == 'help':
                    self._show_example_questions()
                    continue
                
                # 답변 생성
                result = self.answer_question(question)
                
                print("\n" + "=" * 80)
                print(result["answer"])
                print("=" * 80)
                print(f"\n신뢰도: {result['confidence']}")
                
                if result['confidence'] == 'none' and 'available_materials' in result:
                    print("\n사용 가능한 물질 (일부):")
                    for mat in result['available_materials'][:10]:
                        print(f"  - {mat}")
                
            except KeyboardInterrupt:
                print("\n\n시스템을 종료합니다.")
                break
            except Exception as e:
                print(f"\n오류 발생: {e}")
                import traceback
                traceback.print_exc()
    
    def _show_material_list(self):
        """물질 목록 표시"""
        print("\n=== 사용 가능한 물질 목록 ===")
        for i, material in enumerate(self.available_materials, 1):
            print(f"{i}. {material}")
    
    def _show_example_questions(self):
        """예시 질문 표시"""
        examples = [
            "NiO 합성법 알려줘",
            "MgO는 어떻게 합성하나요?",
            "SnO2 합성 절차를 단계별로 설명해주세요",
        ]
        
        print("\n=== 예시 질문 ===")
        for i, example in enumerate(examples, 1):
            print(f"{i}. {example}")

# 1~118 원소 심볼
_ELEMENT_SYMBOLS: Set[str] = {
    "H","He","Li","Be","B","C","N","O","F","Ne",
    "Na","Mg","Al","Si","P","S","Cl","Ar",
    "K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn",
    "Ga","Ge","As","Se","Br","Kr",
    "Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd",
    "In","Sn","Sb","Te","I","Xe",
    "Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu",
    "Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg",
    "Tl","Pb","Bi","Po","At","Rn",
    "Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm","Md","No","Lr",
    "Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Cn","Nh","Fl","Mc","Lv","Ts","Og"
}

# 후보를 넓게 잡는 패턴:
# - MgO, SnO2, LiFePO4
# - (NH4)2SO4, Ca(OH)2
# - CuSO4·5H2O (텍스트에서 '.'로 적히면 '·'로 정규화)
# - 끝 전하 2+, 3-, +2, -3 등(있어도 일단 후보로 잡고, 검증에서 제거)
_CANDIDATE_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (
      (?:
        (?:[A-Z][a-z]?\d*)
        |
        (?:\([A-Za-z0-9]+\)\d*)
      )+
      (?:
        (?:[·\.]\d*)?
        (?:[A-Z][a-z]?\d*|\([A-Za-z0-9]+\)\d*)+
      )*
      (?:\s*(?:\d*[+-]|[+-]\d*))?
    )
    (?![A-Za-z0-9])
    """,
    re.VERBOSE
)

def _normalize_formula(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace(".", "·")  # '.'를 수화물 점으로 통일
    return s

def _strip_charge(s: str) -> str:
    return re.sub(r"(?:\d*[+-]|[+-]\d*)$", "", s)

def _is_valid_formula(candidate: str) -> bool:
    if not candidate:
        return False

    s = _normalize_formula(candidate)
    s = _strip_charge(s)

    # 너무 긴 토큰은 잡음일 확률이 커서 컷(필요시 조정)
    if len(s) > 40:
        return False

    # 수화물 분리: CuSO4·5H2O -> ["CuSO4", "5H2O"]
    parts = s.split("·")

    for part in parts:
        if not part:
            return False

        # 수화물 계수 제거: ex. 5H2O -> H2O
        part = re.sub(r"^\d+", "", part)
        if not part:
            return False

        # 원소 심볼 토큰 추출
        symbols = re.findall(r"[A-Z][a-z]?", part)
        if not symbols:
            return False

        # 모든 심볼이 유효 원소인지 확인
        for sym in symbols:
            if sym not in _ELEMENT_SYMBOLS:
                return False

        # 괄호/영숫자 외 문자 있으면 제외
        if re.search(r"[^A-Za-z0-9\(\)]", part):
            return False

    return True

def extract_chemical_formulas(text: str, *, keep_single_element: bool = False) -> List[str]:
    """
    텍스트에서 등장하는 화학식만 추출해 정렬된 리스트로 반환.
    keep_single_element=False면 'Fe', 'In'처럼 원소 1개짜리 단독 토큰은 기본 제외(오탐 감소).
    """
    if not text:
        return []

    found: Set[str] = set()

    for m in _CANDIDATE_RE.finditer(text):
        cand = _normalize_formula(m.group(1))

        # 오탐 감소: 단일 원소만 있는 경우 제외 (원하면 True로 포함 가능)
        if not keep_single_element and re.fullmatch(r"[A-Z][a-z]?$", cand):
            continue

        if _is_valid_formula(cand):
            found.add(cand)

    return sorted(found)

def main():
    """메인 함수"""
    import sys
    
    # 테스트용 파일 경로
    rdf_file = "/Users/gamjawon/2025-2-prometheus-14Team/Data/merged_all_output_35127items.rdf"
    
    print("\n=== Chemical Synthesis GraphRAG System ===\n")
    
    try:
        rag = SynthesisRAG(rdf_file)
        rag.interactive_mode()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()