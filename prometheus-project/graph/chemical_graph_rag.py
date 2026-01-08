"""
Chemical Synthesis GraphRAG System 
타겟 물질별 합성법 쿼리 지원
"""

from rdflib import Graph, Namespace, RDF, RDFS
from typing import List, Dict, Optional
from collections import defaultdict
import re


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
        """모든 물질 목록 반환"""
        query = """
        PREFIX aiton: <http://www.aitom.com/aiton.owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?materialLabel
        WHERE {
            ?material rdf:type aiton:InorganicMaterial .
            ?material rdfs:label ?materialLabel .
        }
        ORDER BY ?materialLabel
        """
        results = list(self.graph.query(query))
        return [str(row.materialLabel) for row in results]
    
    def query_synthesis_by_target(self, target_material: str) -> Optional[List[Dict]]:
        """
        타겟 물질의 합성법 쿼리
        
        Args:
            target_material: 타겟 물질명 (예: "NiO", "MgO")
        
        Returns:
            합성 단계 리스트 또는 None
        """
        print(f"\n[DEBUG] GraphDB 쿼리: 타겟 물질 = '{target_material}'")
        print("-" * 80)
        
        # 1. 물질 URI 찾기
        material_uri = self._find_material_uri(target_material)
        if not material_uri:
            print(f"❌ 물질 '{target_material}'을(를) 찾을 수 없습니다.")
            return None
        
        print(f"✓ 물질 URI 발견: {material_uri}")
        
        # 2. 합성법 URI 찾기
        synthesis_method_uri = self.graph.value(
            subject=material_uri,
            predicate=self.AITON.hasSynthesisMethod
        )
        
        if not synthesis_method_uri:
            print(f"❌ '{target_material}'의 합성법이 없습니다.")
            return None
        
        print(f"✓ 합성법 URI 발견: {synthesis_method_uri}")
        
        # 3. 첫 번째 단계 찾기
        first_step_uri = self.graph.value(
            subject=synthesis_method_uri,
            predicate=self.AITON.consistOfStep
        )
        
        if not first_step_uri:
            print(f"❌ 합성 단계를 찾을 수 없습니다.")
            return None
        
        print(f"✓ 첫 번째 단계 URI 발견: {first_step_uri}")
        
        # 4. 모든 단계 추출 (nextStep으로 연결)
        sequence = []
        current_step = first_step_uri
        step_num = 1
        
        while current_step and step_num <= 50:  # 무한 루프 방지
            step_info = self._extract_step_info(current_step, step_num)
            if step_info:
                sequence.append(step_info)
                print(f"  Step {step_num}: {step_info['action']}")
            
            # 다음 단계로 이동
            current_step = self.graph.value(
                subject=current_step, 
                predicate=self.AITON.nextStep
            )
            step_num += 1
        
        print(f"✓ 총 {len(sequence)}개 단계 추출 완료")
        print("-" * 80 + "\n")
        
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
        """단계 상세 정보 추출"""
        label = self.graph.value(subject=step_uri, predicate=self.RDFS.label)
        if not label:
            return None
        
        info = {
            "step_number": step_num,
            "action": str(label),
            "precursor": None,
            "solvent": None,
            "condition": None
        }
        
        # 전구체 정보
        precursor = self.graph.value(subject=step_uri, 
                                    predicate=self.AITON.usesPrecursor)
        if precursor:
            prec_label = self.graph.value(subject=precursor, 
                                         predicate=self.RDFS.label)
            info["precursor"] = str(prec_label) if prec_label else None
        
        # 용매 정보
        solvent = self.graph.value(subject=step_uri,
                                  predicate=self.AITON.usesSolvent)
        if solvent:
            solv_label = self.graph.value(subject=solvent,
                                         predicate=self.RDFS.label)
            info["solvent"] = str(solv_label) if solv_label else None
        
        # 조건 정보
        condition = self.graph.value(subject=step_uri,
                                    predicate=self.AITON.performedUnder)
        if condition:
            temp = self.graph.value(subject=condition,
                                   predicate=self.AITON.hasTemperature)
            duration = self.graph.value(subject=condition,
                                       predicate=self.AITON.hasDuration)
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
        synthesis_sequence = self.kg.query_synthesis_by_target(target_material)
        
        if not synthesis_sequence:
            return {
                "answer": f"'{target_material}'의 합성법을 찾을 수 없습니다.",
                "context": [],
                "confidence": "none",
                "available_materials": self.available_materials[:20]
            }
        
        # 3. 컨텍스트 생성
        context_text = self.converter.sequence_to_text(synthesis_sequence, target_material)
        
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


def main():
    """메인 함수"""
    import sys
    
    # 테스트용 파일 경로
    rdf_file = "/mnt/user-data/uploads/merged_all_output_10items.rdf"
    
    print("\n=== Chemical Synthesis GraphRAG System (개선 버전) ===\n")
    
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