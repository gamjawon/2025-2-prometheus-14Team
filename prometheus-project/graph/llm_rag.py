"""
LLM 연동 Chemical Synthesis GraphRAG System 
타겟 물질별 실시간 GraphDB 쿼리 지원
"""

from chemical_graph_rag import ChemicalKnowledgeGraph, TextConverter
from typing import List, Dict, Optional
import os


class LLMSynthesisRAG:
    """LLM 연동 GraphRAG 시스템"""
    
    def __init__(self, rdf_file: str, llm_type: str = "openai", api_key: Optional[str] = None):
        """
        Args:
            rdf_file: RDF 파일 경로
            llm_type: "openai" 또는 "claude"
            api_key: API 키 (없으면 환경변수에서 읽음)
        """
        self.kg = ChemicalKnowledgeGraph(rdf_file)
        self.converter = TextConverter()
        self.llm_type = llm_type
        
        # API 설정
        if api_key:
            self.api_key = api_key
        else:
            if llm_type == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif llm_type == "claude":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError(f"{llm_type} API 키가 필요합니다.")
        
        # LLM 클라이언트 초기화
        self._init_llm_client()
        
        # 사용 가능한 물질 목록 로드
        print("\n사용 가능한 물질 목록 로드 중...")
        self.available_materials = self.kg.list_all_materials()
        print(f"✓ 총 {len(self.available_materials)}개 물질")
        if len(self.available_materials) <= 20:
            print(f"  물질 목록: {', '.join(self.available_materials)}")
        print()
    
    def _init_llm_client(self):
        """LLM 클라이언트 초기화"""
        if self.llm_type == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                print(f"✓ OpenAI 클라이언트 초기화 완료")
            except ImportError:
                raise ImportError("openai 패키지를 설치하세요: pip install openai")
        
        elif self.llm_type == "claude":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                print(f"✓ Claude 클라이언트 초기화 완료")
            except ImportError:
                raise ImportError("anthropic 패키지를 설치하세요: pip install anthropic")
    
    def answer_question(self, question: str) -> Dict:
        """질문에 답변 (LLM 사용)"""
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
                "source": "none",
                "available_materials": self.available_materials[:20]
            }
        
        print(f"\n✓ 타겟 물질 인식: '{target_material}'")
        
        # 2. GraphDB에서 실시간 쿼리 - 해당 물질의 합성법만 가져오기
        synthesis_sequence = self.kg.query_synthesis_by_target(target_material)
        
        if not synthesis_sequence:
            return {
                "answer": f"'{target_material}'의 합성법을 찾을 수 없습니다.",
                "context": [],
                "confidence": "none",
                "source": "knowledge_graph",
                "available_materials": self.available_materials[:20]
            }
        
        # 3. 컨텍스트 생성
        context_text = self.converter.sequence_to_text(synthesis_sequence, target_material)
        
        # 디버깅: LLM에 전달될 컨텍스트 출력
        print("\n" + "="*80)
        print("[DEBUG] LLM에게 전달될 컨텍스트:")
        print("="*80)
        print(context_text)
        print("="*80 + "\n")
        
        # 4. LLM으로 답변 생성
        answer = self._generate_llm_answer(question, context_text, target_material)
        
        # 디버깅: 전체 처리 요약
        print("\n" + "="*80)
        print("[DEBUG] 처리 완료 요약:")
        print("="*80)
        print(f"  타겟 물질: {target_material}")
        print(f"  추출된 단계 수: {len(synthesis_sequence)}개")
        print(f"  컨텍스트 길이: {len(context_text)} 글자")
        print(f"  LLM 답변 길이: {len(answer)} 글자")
        print("="*80 + "\n")
        
        return {
            "answer": answer,
            "context": [context_text],
            "confidence": "high",
            "source": "knowledge_graph",
            "target_material": target_material
        }
    
    def _extract_target_material(self, question: str) -> Optional[str]:
        """질문에서 타겟 물질 추출"""
        question_lower = question.lower()
        
        # 긴 물질명부터 체크 (예: "LiFePO₄"를 "Fe"보다 먼저 매칭)
        # "Fe"가 "LiFePO₄" 안에 포함되어 있어서 길이순 정렬 필수!
        sorted_materials = sorted(self.available_materials, key=len, reverse=True)
        
        # 사용 가능한 물질 목록에서 매칭
        for material in sorted_materials:
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
    
    def _generate_llm_answer(self, question: str, context: str, material: str) -> str:
        """LLM으로 답변 생성"""
        # 시스템 프롬프트
        system_prompt = f"""당신은 화학 합성 전문가입니다. 
주어진 '{material}' 물질의 지식 그래프 정보를 바탕으로 정확하고 명확하게 답변하세요.

규칙:
1. 제공된 지식 그래프 정보만 사용하세요
2. 정보가 불충분하면 그렇게 말하세요
3. 단계별로 명확하게 설명하세요
4. 전문 용어는 간단히 설명을 덧붙이세요
5. 한국어로 답변하세요
6. 답변은 자연스러운 문장으로 작성하세요"""
        
        # 사용자 프롬프트
        user_prompt = f"""지식 그래프 정보:
{context}

질문: {question}

위 '{material}' 합성법 정보를 바탕으로 답변해주세요."""
        
        # 디버깅: LLM에 전달될 전체 프롬프트 출력
        print("\n" + "="*80)
        print("[DEBUG] LLM API 호출 - 시스템 프롬프트:")
        print("="*80)
        print(system_prompt)
        print("\n" + "="*80)
        print("[DEBUG] LLM API 호출 - 사용자 프롬프트:")
        print("="*80)
        print(user_prompt)
        print("="*80 + "\n")
        
        print("[LLM 답변 생성 중...]")
        
        # LLM 호출
        if self.llm_type == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self.llm_type == "claude":
            return self._call_claude(system_prompt, user_prompt)
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI API 호출"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            answer = response.choices[0].message.content
            
            # 디버깅: API 호출 성공
            print(f"\n[DEBUG] ✓ OpenAI API 호출 성공")
            print(f"[DEBUG] 생성된 답변 길이: {len(answer)} 글자")
            print(f"[DEBUG] 토큰 사용량: {response.usage.total_tokens} tokens\n")
            
            return answer
        except Exception as e:
            error_msg = f"OpenAI API 오류: {str(e)}"
            print(f"\n[DEBUG] ✗ OpenAI API 호출 실패: {error_msg}\n")
            return error_msg
    
    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Claude API 호출"""
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            answer = response.content[0].text
            
            # 디버깅: API 호출 성공
            print(f"\n[DEBUG] ✓ Claude API 호출 성공")
            print(f"[DEBUG] 생성된 답변 길이: {len(answer)} 글자")
            print(f"[DEBUG] 토큰 사용량: input={response.usage.input_tokens}, output={response.usage.output_tokens}\n")
            
            return answer
        except Exception as e:
            error_msg = f"Claude API 오류: {str(e)}"
            print(f"\n[DEBUG] ✗ Claude API 호출 실패: {error_msg}\n")
            return error_msg
    
    def interactive_mode(self):
        """대화형 모드"""
        print("=" * 80)
        print(f"Chemical Synthesis GraphRAG System (LLM: {self.llm_type.upper()})")
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
                print(f"\n출처: {result['source']}")
                print(f"신뢰도: {result['confidence']}")
                
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
        # 실제 사용 가능한 물질로 예시 생성
        examples = []
        if len(self.available_materials) >= 3:
            examples = [
                f"{self.available_materials[0]} 합성법을 단계별로 설명해주세요",
                f"{self.available_materials[1]}는 어떻게 합성하나요?",
                f"{self.available_materials[2]} 합성의 핵심 단계는 무엇인가요?",
            ]
        else:
            examples = [
                "NiO 합성법을 단계별로 설명해주세요",
                "MgO는 어떻게 합성하나요?",
                "SnO2 합성의 핵심 단계는 무엇인가요?",
            ]
        
        print("\n=== 예시 질문 ===")
        for i, example in enumerate(examples, 1):
            print(f"{i}. {example}")


def main():
    """메인 함수"""
    import sys
    from dotenv import load_dotenv  
    
    # .env 파일에서 환경변수 로드
    load_dotenv()  
    
    # 테스트용 파일 경로
    rdf_file = "/Users/gamjawon/2025-2-prometheus-14Team/prometheus-project/graph/GraphDB/merged_all_output_35127items.rdf"
    
    print("\n=== LLM 연동 Chemical Synthesis GraphRAG (개선 버전) ===\n")
    
    try:
        # OpenAI 사용 (또는 Claude 사용 시 llm_type="claude"로 변경)
        api_key = os.getenv("OPENAI_API_KEY")
        rag = LLMSynthesisRAG(rdf_file, llm_type="openai", api_key=api_key)
        rag.interactive_mode()
            
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()