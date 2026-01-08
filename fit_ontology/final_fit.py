# LLM이 합성 단계 추론 지시 

import json
import os
import sys
from typing import Any, Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_inorganic_material(extracted: Dict[str, Any], idx: int) -> Dict[str, Any]:
    target = extracted.get("target", {}) or {}
    reaction_string = extracted.get("reaction_string")
    mat = {
        "id": f"inorg_{idx}",
        "class": "InorganicMaterial",
        "hasName": target.get("material_string") or target.get("material_formula"),
        "hasAcronym": target.get("is_acronym"),
        "hasPhase": target.get("phase") or "",
        "isOxygenDeficiency": target.get("oxygen_deficiency"),
        "hasReaction": reaction_string
    }
    return mat


def to_precursors(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    abstract Precursor entry template only: class + key(값 없음)
    값은 LLM이 step 전체 usesPrecursor에서 unique하게 추론해 채움
    """
    # 빈 값(혹은 None), key 구조만 draft로 포함
    return [
        {
            "class": "Precursor",
            "hasName": None
        }
    ]


def to_solvents(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    sols = []
    for i, s in enumerate(extracted.get("solvents_string", []), start=1):
        sols.append({
            "id": f"solvent_{i}",
            "class": "Solvent",
            "hasName": s
        })
    return sols


def to_media(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    medias = []
    seen = set()

    for op in extracted.get("operations", []):
        cond = op.get("conditions") or {}
        mm = cond.get("mixing_media")
        if not mm:
            continue
        # mixing_media가 리스트라고 가정 (["water"], ["ethanol", "water"] 등)
        for name in mm:
            if name not in seen:
                seen.add(name)
                medias.append({
                    "id": f"media_{len(medias) + 1}",
                    "class": "Media",
                    "hasName": name
                })

    return medias


#def to_abrasives(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    abrasives = []
    for i, a in enumerate(extracted.get("abrasives", []), start=1):
        abrasives.append({
            "id": f"abrasive_{i}",
            "class": "Abrasive",
            "hasName": a
        })
    return abrasives

def to_additives(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    adds = []
    for i, a in enumerate(extracted.get("additives", []), start=1):
        adds.append({
            "id": f"additive_{i}",
            "class": "Additive",
            "hasName": a.get("material_string") or a.get("material_formula") or a
        })
    return adds


def condition_from_operation(op: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
    conds = op.get("conditions") or {}
    if not conds:
        return None

    def extract_with_unit(block):
        """block에서 values[0]과 units를 결합해 문자열로 반환"""
        if not isinstance(block, dict):
            return None
        value = None
        unit = block.get("units")
        v = block.get("values")
        if isinstance(v, list) and v:
            value = v[0]
        elif "value" in block:
            value = block["value"]
        if value is None:
            return None
        if unit:
            return f"{value} {unit}"
        return str(value)

    temp = extract_with_unit(conds.get("temperature"))
    time_ = extract_with_unit(conds.get("time"))
    ph = conds.get("pH")
    pressure = extract_with_unit(conds.get("pressure"))

    if all(v is None for v in [temp, time_, ph, pressure]):
        return None

    return {
        "id": f"cond_{idx}",
        "class": "Condition",
        "hasTemperature": temp,
        "hasTime": time_,
        "haspH": str(ph) if ph is not None else None,
        "hasPressure": pressure
    }


def to_synthesis_steps(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    JSON 데이터셋에서 직접적으로 알 수 있는 정보만 사용해서
    SynthesisStep 리스트를 만든다.

    - operations[*] → step 시퀀스 (id, hasAction)
    - condition_from_operation → performedUnder (Condition id)
    - nextStep 체인

    어떤 step이 어떤 Precursor/Solvent/Media/Additive/Product를
    사용하는지는 여기서 전혀 넣지 않는다.
    그 부분은 LLM이 ontology와 extracted를 보고 추론하도록 맡긴다.
    """
    steps: List[Dict[str, Any]] = []
    ops = extracted.get("operations", []) or []

    for i, op in enumerate(ops, start=1):
        step_id = f"step_{i}"
        cond = condition_from_operation(op, i)

        step: Dict[str, Any] = {
            "id": step_id,
            "class": "SynthesisStep",
            "hasAction": op.get("string") or op.get("type"),
            "hasNote": None
        }

        # JSON에서 직접적으로 알 수 있는 것은 "이 step이 어떤 조건에서 수행되는가" 뿐
        if cond:
            step["performedUnder"] = cond["id"]

        steps.append(step)

    # step 순서 정보는 JSON의 operations 순서를 그대로 사용
    for i in range(len(steps) - 1):
        steps[i]["nextStep"] = steps[i + 1]["id"]

    return steps



def to_product(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    abstract Product entry template only: class + key(값 없음)
    값은 LLM이 step 전체 producesProduct에서 unique하게 추론해 채움
    """
    return [
        {
            "class": "Product",
            "hasName": None
        }
    ]

def to_synthesis_method(extracted: Dict[str, Any], first_step_id: Optional[str]) -> Dict[str, Any]:
    """
    extracted["operations"]의 개수만큼 step id를 만들어서, 
    'consistOfStep' 필드에 순서대로 리스트로 채우기.
    """
    method = {
        "id": "method_1",
        "class": "SynthesisMethod",
        "hasID": 1
    }
    
    # operations에서 step id 리스트 생성
    ops = extracted.get("operations", []) or []
    step_ids = [f"step_{i+1}" for i in range(len(ops))]
    
    if step_ids:
        # 한 개 이상 step이 있으면 리스트로 입력
        # (step이 1개이면 단일 string으로도 할 수 있지만, 일관성을 위해 리스트로)
        method["consistOfStep"] = step_ids
    
    return method


def fit_extracted_to_ontology(extracted: Dict[str, Any],
                              ontology: Dict[str, Any],
                              idx: int) -> Dict[str, Any]:
    inorg = to_inorganic_material(extracted, idx)
    precs = to_precursors(extracted)
    sols = to_solvents(extracted)
    meds = to_media(extracted)
    # abrasives = to_abrasives(extracted)  # 필요하면 다시 사용
    prod = to_product(extracted)
    adds = to_additives(extracted)

    # 🔥 step에는 구조/조건만 넣고, 어떤 물질을 쓰는지는 LLM에게 맡김
    steps = to_synthesis_steps(extracted)

    method = to_synthesis_method(extracted, steps[0]["id"] if steps else None)

    conditions = []
    ops = extracted.get("operations", []) or []
    for i, op in enumerate(ops, start=1):
        c = condition_from_operation(op, i)
        if c:
            conditions.append(c)

    result = {
        "InorganicMaterial": [inorg],
        "Precursor": precs,
        "Solvent": sols,
        "Media": meds,
        # "Abrasive": abrasives,
        "Product": [prod],
        "Additive": adds,
        "SynthesisMethod": [method],
        "SynthesisStep": steps,
        "Condition": conditions
    }
    return result


def llm_refine_with_ontology(
    extracted: Dict[str, Any],
    ontology: Dict[str, Any],
    draft: Dict[str, Any]
) -> Dict[str, Any]:
    """
    LLM에게 ontology와 draft(result)를 같이 주고
    'ontology에 정의된 클래스/프로퍼티만 사용해서 다시 만들어줘'라고 시킨다.
    draft는 네 rule-based 결과라서 LLM이 '아 이런 식으로 매핑하려고 했구나' 하고 보완할 수 있음.
    """
    #입력 데이터로 해야할 일 정의 
    user_payload = {
        "instruction": (
    "다음 세 가지 정보를 바탕으로, 온톨로지에 완전히 부합하는 합성 데이터 JSON을 만들어라. "
    "1) ontology: 사용할 수 있는 클래스, 오브젝트 프로퍼티, 데이터 프로퍼티 정의 "
    "2) extracted: 논문에서 추출된 원본 JSON "
    "3) draft: 사용자가 규칙 기반으로 1차 변환한 결과(여기에 step 시퀀스와 조건, 물질 리스트가 있지만, 각 step에 어떤 물질이 연결되는지는 비워져 있다.) "

    "너의 주요 역할은 각 SynthesisStep에 어떤 Precursor, Solvent, Media, Additive, Product가 연결되는지 추론하여 "
    "usesPrecursor, usesSolvent, usesMedia, usesAdditive, producesProduct, performedUnder, nextStep, consistOfStep 등 프로퍼티를 채우는 것이다. "
    "extracted.operations의 순서를 따라 step 시퀀스를 구성하라. "

    "하나의 data 안의 모든 물질(entity)은 반드시 SynthesisStep 내에서 최소한 한 번은 usesPrecursor, usesSolvent, usesMedia, usesAdditive, producesProduct 등으로 step에 연결되어 있어야 한다. "
    "어떤 물질도 step 연결에서 누락되면 안 된다. "

    "추론 시, extracted의 paragraph_string, operations, reaction, quantities 등에 근거가 없는 정보는 절대 임의로 만들지 말고, "
    "확실하지 않으면 해당 프로퍼티는 아예 넣지 않거나 null/빈 배열로 두어라. "
    "반드시 ontology에 정의된 이름(프로퍼티, 클래스 등)만 써라. "

    "특히 SynthesisStep 내부에서 usesPrecursor, producesProduct 등은 chemical id를 절대 쓰지 말고, 반드시 실제 물질명(예: \"La(NO3)3·6H2O\", \"BaTiO3\" 등)을 값으로 써라. "
    "여러 개 물질이 한 단계에 쓰이면 리스트로 표기하라 (예: [\"TiCl4\", \"La(NO3)3·6H2O\"]). "
    "값이 없거나 불확실한 key는 null이나 빈 배열로 두어도 된다. "
    "각 step의 input/output 연결관계 정확성에 집중하라. "

    "각 step의 usesPrecursor, producesProduct 등에서 등장한 모든 unique 물질명을 중복 없이 각 Precursor/Product 필드에 하나씩만 포함시켜야 한다. "
    "draft에서는 hasName이 None이지만, 최종 output은 반드시 해당 값으로 채워야 한다. 예시:\n"
    "\"Precursor\": [\n  { \"class\": \"Precursor\", \"hasName\": \"Al(NO3)3·9H2O\" }, ... ],\n"
    "\"Product\": [\n  { \"class\": \"Product\", \"hasName\": \"Pt-In/Mg(Pt)(In)(Al)Ox\" }, ... ]\n"
    "값이 없으면 빈 배열로 두어도 된다. "

    "SynthesisStep 출력은 반드시 아래 예시 패턴처럼, id, class, hasAction, hasNote, nextStep 등 주요 키 구조를 항상 포함하고, usesPrecursor/producesProduct/usesSolvent/usesMedia 같은 연결 정보는 상황에 맞게 값을 채우되, 해당 값이 없으면 null이나 빈 배열로 표기하라. "
    "예시 1:\n"
    "{\n"
    "  \"id\": \"step_1\",\n"
    "  \"class\": \"SynthesisStep\",\n"
    "  \"hasAction\": \"adding\",\n"
    "  \"hasNote\": null,\n"
    "  \"nextStep\": \"step_2\",\n"
    "  \"usesPrecursor\": \"La(NO3)3·6H2O\",\n"
    "  \"usesSolvent\": \"water\",\n"
    "  \"usesMedia\": null\n"
    "}\n"
    "예시 2:\n"
    "{\n"
    "  \"id\": \"step_5\",\n"
    "  \"class\": \"SynthesisStep\",\n"
    "  \"hasAction\": \"washed\",\n"
    "  \"hasNote\": null,\n"
    "  \"nextStep\": \"step_6\",\n"
    "  \"usesSolvent\": \"ethanol\"\n"
    "  \"producesProduct\": \"BaTiO3\"\n"
    "}\n"
    "이 구조와 key 패턴(순서 포함)을 모든 step에 일관되게 적용하여 SynthesisStep 리스트를 만들어라. "
    "draft는 내가 원하는 출력 온톨로지 표준 스키마이니, SynthesisStep 이외의 모든 필드는 값과 구조를 단 하나도 수정하지 말고 draft 그대로 출력할 것."
    "특히, quantities field 안의 material도 precursor, media등이 될 수 있으니 적절히 분류하여 step에 반영해라."
    "실험 맥락상 어떤 역할로 쓰였는지 추론(예: 보조제, 첨가제, 매질 등)해 옳은 class/step에 넣고, "
    "모든 물질을 절대 누락하지 말 것."
    "quantities field 안에 material이 있는지 꼭 확인할 것"
    "모든 물질의 클래스 할당, step 연결정보 결정 등은 반드시 step-by-step, 원인과 맥락을 논리적으로 고려하는 'chain of thought' (COT) 방식의 reasoning을 내부적으로 거쳐라. "
    "실제로 reasoning 과정을 출력할 필요는 없지만, 모든 결정(분류, 연결, 값 채움)은 위 논리적 COT 과정을 한 번씩 거친 뒤 결과를 내놓을 것."
    )

    


,

        "ontology": ontology,
        "extracted": extracted,
        "draft": draft
    }

    messages = [
        {   #역할 부여 (꼭 지켜야하는 )
            "role": "system",
            "content": (
                "당신은 사용자 정의 온톨로지에 맞춰 JSON을 재구성하는 보조자이며 이 세상 최고의 화학자입니다. "
                "온톨로지에 없는 클래스나 프로퍼티는 절대 추가하지 마세요. "
                "domain과 range 정보가 있을 경우 이를 우선적으로 따르세요. "
                "반드시 JSON 객체 하나만 출력하세요."
                "ontology.json의 description 필드에 설명되는 내용을 참고하세요."
                "추론을 할 수는 있지만, extracted JSON에 전혀 등장하지 않는 "
                "새로운 물질이나 step은 절대 만들지 마세요. "
                "입력되는 draft는 내가 원하는 출력 온톨로지 표준 스키마다. "
                "모든 필드(Precursor, InorganicMaterial 등)는 값과 구조를 단 하나도 수정하지 말고 draft 그대로 출력할 것. "
                "단, 오직 SynthesisStep 필드만 LLM이 추론하여 usesPrecursor, usesAdditive, usesMedia 등 연결 정보를 자유롭게 채워라. "
                "SynthesisStep의 각 step 객체 키 구조는 draft와 완전히 일치시켜야 하지만, 값은 LLM이 ontology 및 extracted evidence를 근거로 채운다. "
                "SynthesisStep 이외 그 어떤 필드/구조도 추가, 삭제, 순서변경, 값수정 하지 말 것. "
                "값이 확실치 않으면 null이나 빈 배열/객체로 남겨라."
                "당신이 정확히 synthesisstep내용을 추론하지 않으면 많은 사람들이 죽을 수도 있습니다."
                "그러니 정확히 추론하고 hallucination을 최대한 방지하세요."
            )
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False)
        }
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=messages
    )

    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        # 혹시 코드블록이나 앞뒤 텍스트가 붙으면 best-effort 파싱
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
        else:
            raise

def main():
    extracted_path = "data/test.json" #원본 data경로 
    ontology_path = "myontology/ontology.json" #온톨로지 경로 
    output_path = "test.json" #출력할 파일 경로 

    with open(extracted_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, str):
    # 이중 serialization 등으로 인한 오류일 수 있으니 다시 파싱
     data = json.loads(data)
    if isinstance(data, dict):
        all_extracted = [data]
    elif isinstance(data, list):
        all_extracted = data
    else:
        raise TypeError("Input data is not list/dict.")

    ontology = load_json(ontology_path)
    results = []
    for idx, extracted in enumerate(all_extracted, start=1):
        doi = extracted.get("doi", "NO_DOI")
        print(f"[INFO] ({idx}/{len(all_extracted)}) 변환 중: 논문 DOI = {doi}")
        # 1. 규칙 기반 draft
        draft = fit_extracted_to_ontology(extracted, ontology, idx)
        # 2. LLM 보정
        refined = llm_refine_with_ontology(extracted, ontology, draft)
        results.append(refined)

    # 리스트 또는 논문ID/doi 등과 함께 출력
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved {len(results)} records to '{output_path}' ✅")




if __name__ == "__main__":
    main()
