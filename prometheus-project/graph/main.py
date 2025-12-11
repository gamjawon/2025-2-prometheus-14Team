#!/usr/bin/env python3
"""
JSON 구조 변환 및 RDF 변환 통합 스크립트 (최종 수정 버전)
리스트의 각 항목을 {'extracted': item} 형태로 감싸서 처리
"""

from json_to_rdf_converter import JSONtoRDFConverter
from rdf_visualizer import visualize_rdf_graph
from rdf_graph_builder import RDFGraphBuilder
import sys
import os
import json
from collections import Counter


def merge_builders(builders):
    """여러 RDFGraphBuilder를 하나로 병합"""
    if not builders:
        return None
    
    # 첫 번째 builder를 기준으로 시작
    merged = builders[0]
    
    # 나머지 builder들의 노드와 엣지를 추가
    for builder in builders[1:]:
        # 노드 추가 (중복 확인)
        existing_ids = {node.node_id for node in merged.nodes}
        for node in builder.nodes:
            if node.node_id not in existing_ids:
                merged.nodes.append(node)
                existing_ids.add(node.node_id)
        
        # 엣지 추가 (중복 확인) - 속성명 수정: from_node→source, relation→edge_type, to_node→target
        existing_edges = {(e.source, e.edge_type, e.target) for e in merged.edges}
        for edge in builder.edges:
            edge_tuple = (edge.source, edge.edge_type, edge.target)
            if edge_tuple not in existing_edges:
                merged.edges.append(edge)
                existing_edges.add(edge_tuple)
    
    return merged


def wrap_item_for_converter(item):
    """
    각 항목을 converter가 기대하는 형태로 변환
    {'InorganicMaterial': [...], 'Precursor': [...]} 
    -> {'extracted': {'InorganicMaterial': [...], 'Precursor': [...]}}
    """
    return {'extracted': item}


def main():
    """메인 함수"""
    
    print("\n" + "="*60)
    print("🔄 LLM JSON → RDF 그래프 변환기 (대용량 처리)")
    print("="*60)
    
    # 1. 파일 경로 확인
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "/Users/gamjawon/2025-2-prometheus-14Team/Data/merged_all.json"
        print(f"\n💡 사용법: python convert_large_json.py <json_file>")
        print(f"   기본 파일 사용: {json_file}")
    
    if not os.path.exists(json_file):
        print(f"\n❌ 오류: 파일을 찾을 수 없습니다: {json_file}")
        return
    
    # 2. 온톨로지 파일 확인
    ontology_file = "/Users/gamjawon/2025-2-prometheus-14Team/prometheus-project/ontology/aitom_inorganic.rdf"
    if not os.path.exists(ontology_file):
        print(f"\n❌ 오류: 온톨로지 파일이 없습니다: {ontology_file}")
        return
    
    # 3. 처리 옵션 입력
    print(f"\n📄 JSON 파일 읽는 중: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print("❌ 리스트 형태의 JSON이 아닙니다.")
        return
    
    total_items = len(data)
    print(f"📦 총 {total_items:,}개 항목 발견")
    
    # 처리할 항목 수 결정
    print(f"\n⚠️  주의: {total_items:,}개 항목을 모두 처리하면 시간이 오래 걸립니다.")
    print(f"💡 옵션:")
    print(f"   1. 전체 처리 (시간 소요: 예상 {total_items//100} ~ {total_items//50}분)")
    print(f"   2. 샘플 처리 (빠른 테스트용)")
    
    choice = input(f"\n선택 (1=전체, 2=샘플, 기본=샘플): ").strip() or "2"
    
    if choice == "1":
        items_to_process = data
        print(f"\n✅ 전체 {len(items_to_process):,}개 항목 처리")
    else:
        # 샘플 개수 입력
        sample_size = input(f"샘플 개수 입력 (기본=100): ").strip() or "100"
        try:
            sample_size = min(int(sample_size), total_items)
        except:
            sample_size = 100
        items_to_process = data[:sample_size]
        print(f"\n✅ 처음 {len(items_to_process):,}개 항목만 처리")
    
    # 4. 변환 시작
    print(f"\n🔄 변환 시작...\n")
    
    converter = JSONtoRDFConverter(ontology_file=ontology_file)
    all_builders = []
    failed_count = 0
    
    for idx, item in enumerate(items_to_process):
        if (idx + 1) % 100 == 0 or idx == 0 or (idx + 1) == len(items_to_process):
            print(f"진행: {idx+1:,}/{len(items_to_process):,} ({(idx+1)/len(items_to_process)*100:.1f}%)")
        
        # 임시 파일로 저장 (wrapped 형태)
        temp_file = f"temp_item_{idx}.json"
        wrapped_item = wrap_item_for_converter(item)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(wrapped_item, f, ensure_ascii=False, indent=2)
        
        try:
            builder = converter.convert_json_to_graph(temp_file)
            all_builders.append(builder)
        except Exception as e:
            failed_count += 1
            if failed_count <= 5:  # 처음 5개 에러만 출력
                print(f"   ⚠️  항목 {idx+1} 실패: {str(e)[:100]}")
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    if not all_builders:
        print("\n❌ 처리된 항목이 없습니다.")
        return
    
    success_count = len(all_builders)
    print(f"\n✅ 변환 완료: {success_count:,}개 성공, {failed_count:,}개 실패")
    
    # 5. 그래프 병합
    print(f"\n🔄 {len(all_builders):,}개 그래프 병합 중...")
    builder = merge_builders(all_builders)
    
    # 6. 통계 출력
    print(f"\n📊 최종 통계:")
    print(f"   노드: {len(builder.nodes):,}개")
    print(f"   엣지: {len(builder.edges):,}개")
    
    # 노드 타입별 카운트
    node_types = Counter(n.node_type for n in builder.nodes)
    print(f"\n📈 노드 타입별 분포:")
    for node_type, count in node_types.most_common(10):
        print(f"   {node_type}: {count:,}개")
    if len(node_types) > 10:
        print(f"   ... 외 {len(node_types)-10}개 타입")
    
    # 7. RDF 파일 저장
    base_name = os.path.basename(json_file).replace('.json', '')
    output_rdf = f"{base_name}_output_{success_count}items.rdf"
    
    print(f"\n💾 RDF 파일 저장 중: {output_rdf}")
    builder.save(output_rdf)
    
    # 8. 시각화 (옵션)
    output_png = f"{base_name}_graph_{success_count}items.png"
    
    if len(builder.nodes) > 500:
        print(f"\n⚠️  노드가 {len(builder.nodes):,}개로 너무 많아 시각화를 건너뜁니다.")
        print(f"   (시각화는 500개 이하 노드에서 권장)")
    else:
        print(f"\n🎨 그래프 시각화 중: {output_png}")
        try:
            visualize_rdf_graph(
                output_rdf,
                output_png,
                f"Synthesis Processes ({success_count} items)"
            )
        except Exception as e:
            print(f"⚠️  시각화 실패: {e}")
    
    # 9. 완료 메시지
    print("\n" + "="*60)
    print("✨ 모든 작업 완료!")
    print("="*60)
    print(f"\n생성된 파일:")
    print(f"  📄 RDF 그래프: {output_rdf}")
    if os.path.exists(output_png):
        print(f"  🖼️  시각화:    {output_png}")
    
    # 10. 추가 정보
    print(f"\n💡 다음 단계:")
    print(f"  1. RDF 파일 확인: head -100 {output_rdf}")
    if os.path.exists(output_png):
        print(f"  2. 시각화 확인:  open {output_png}")
    print(f"  3. 전체 처리:     python {sys.argv[0]} (옵션 1 선택)")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        print("\n상세 오류 정보:")
        traceback.print_exc()