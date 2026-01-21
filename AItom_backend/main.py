"""
FastAPI backend for Safety Check Model Inference
"""
import os
import sys
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List

import torch
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# Safety_Check_Model 경로를 sys.path에 추가
SAFETY_MODEL_DIR = Path(__file__).parent / "Safety_Check_Model" / "safety_embedding_model"
if str(SAFETY_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(SAFETY_MODEL_DIR))

from utils.multi_property_embedding import get_combined_embedding, DEFAULT_PROPERTIES
from model import RiskClassifier

# Prometheus GraphRAG 경로를 sys.path에 추가
PROMETHEUS_GRAPH_DIR = Path(__file__).parent.parent / "prometheus-project" / "graph"
if str(PROMETHEUS_GRAPH_DIR) not in sys.path:
    sys.path.insert(0, str(PROMETHEUS_GRAPH_DIR))

from llm_rag import LLMSynthesisRAG


@contextmanager
def change_working_dir(path: Path):
    """작업 디렉토리를 임시로 변경하는 context manager"""
    original_cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_cwd)

# FastAPI 앱 생성
app = FastAPI(
    title="AItom API",
    description="무기물 합성법 제공 챗봇",
    version="1.0.0"
)

# 전역 변수
model = None
device = None
model_config = None
rag_system = None  # GraphRAG 시스템

# 데이터베이스 설정
DB_PATH = Path(__file__).parent / "users.db"
security = HTTPBearer()

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def init_db():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호 검증"""
    return hash_password(password) == password_hash


def create_user(username: str, password: str) -> bool:
    """사용자 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # 사용자명 중복
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> bool:
    """사용자 인증"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result is None:
        return False
    
    password_hash = result[0]
    return verify_password(password, password_hash)


def get_user_id(username: str) -> Optional[int]:
    """사용자 ID 조회"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """JWT 토큰 검증 및 사용자명 반환"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """현재 인증된 사용자 반환 (의존성 함수)"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def load_model():
    """모델 로드"""
    global model, device, model_config
    
    # 디바이스 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 모델 체크포인트 경로
    checkpoint_path = SAFETY_MODEL_DIR / "training_results" / "best_model6.pth"
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")
    
    # 체크포인트 로드
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # 모델 설정 추출
    properties = checkpoint.get('properties', DEFAULT_PROPERTIES)
    hidden_dims = checkpoint.get('hidden_dims', [256, 128, 64, 32])
    
    # input_dim 추론: state_dict에서 첫 번째 레이어의 in_features 확인
    input_dim = len(properties) * 3  # 기본값: properties 개수 * 3
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
        # network.0.weight의 shape에서 input_dim 추론 (shape: [out_features, in_features])
        first_layer_key = 'network.0.weight'
        if first_layer_key in state_dict:
            input_dim = state_dict[first_layer_key].shape[1]
        else:
            # 키 이름이 다를 수 있으니 첫 번째 Linear 레이어 찾기
            for key in sorted(state_dict.keys()):
                if 'weight' in key and 'network' in key:
                    input_dim = state_dict[key].shape[1]
                    break
    
    model_config = {
        'input_dim': input_dim,
        'hidden_dims': hidden_dims,
        'properties': properties,
    }
    
    # 모델 초기화
    model = RiskClassifier(
        input_dim=model_config['input_dim'],
        hidden_dims=model_config['hidden_dims'],
        dropout_rate=0,  # 추론 시 dropout 비활성화
    )
    
    # 모델 가중치 로드
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()  # 평가 모드
    
    print(f"Model loaded successfully from {checkpoint_path}")
    print(f"Model config: {model_config}")


def load_rag_system():
    """GraphRAG 시스템 로드"""
    global rag_system
    
    # RDF 파일 경로 설정 (프로젝트 루트의 Data 폴더)
    rdf_file = Path(__file__).parent.parent / "Data" / "merged_all_output_35127items.rdf"
    
    if not rdf_file.exists():
        print(f"Warning: RDF file not found at {rdf_file}. GraphRAG API will not be available.")
        return
    
    try:
        # LLM 타입 및 API 키 설정 (환경변수에서 읽음)
        llm_type = os.getenv("LLM_TYPE", "openai")  # "openai" or "claude"
        api_key = None
        if llm_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif llm_type == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            print(f"Warning: {llm_type.upper()} API key not found. GraphRAG API will not be available.")
            return
        
        rag_system = LLMSynthesisRAG(
            rdf_file=str(rdf_file),
            llm_type=llm_type,
            api_key=api_key
        )
        print(f"GraphRAG system loaded successfully from {rdf_file}")
    except Exception as e:
        print(f"Error loading GraphRAG system: {e}")
        import traceback
        traceback.print_exc()


# 앱 시작 시 모델 로드 및 DB 초기화
@app.on_event("startup")
async def startup_event():
    init_db()
    load_model()
    load_rag_system()


# Request/Response 모델
class SafetyCheckRequest(BaseModel):
    formula: str
    verbose: Optional[bool] = False


class SafetyCheckResponse(BaseModel):
    formula: str
    is_risky: bool
    probability_risky: float
    probability_safe: float
    prediction: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    message: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    message: str
    username: str
    token: str


class SynthesisQuestionRequest(BaseModel):
    question: str


class SynthesisAnswerResponse(BaseModel):
    answer: str
    context: List[str]
    confidence: str
    source: str
    target_material: Optional[str] = None
    extracted_formulas: Optional[List[str]] = None
    chosen_method_index: Optional[int] = None
    chosen_method_label: Optional[str] = None
    method_count: Optional[int] = None
    synthesis_type: Optional[str] = None
    synthesis_type_confidence: Optional[str] = None
    synthesis_type_reason: Optional[str] = None
    available_materials: Optional[List[str]] = None


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Safety Check API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    회원가입 엔드포인트
    
    - **username**: 사용자 아이디
    - **password**: 비밀번호
    
    Returns:
    - **message**: 회원가입 성공 메시지
    - **username**: 가입한 사용자명
    """
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    
    success = create_user(request.username, request.password)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    return RegisterResponse(
        message="Registration successful",
        username=request.username
    )


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    로그인 엔드포인트
    
    - **username**: 사용자 아이디
    - **password**: 비밀번호
    
    Returns:
    - **message**: 로그인 성공 메시지
    - **username**: 로그인한 사용자명
    - **token**: JWT 인증 토큰 (24시간 유효)
    """
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    if not authenticate_user(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # JWT 토큰 생성
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": request.username}, expires_delta=access_token_expires
    )
    
    return LoginResponse(
        message="Login successful",
        username=request.username,
        token=access_token
    )


@app.post("/predict", response_model=SafetyCheckResponse)
async def predict(
    request: SafetyCheckRequest,
    current_user: str = Depends(get_current_user)
):
    """
    화학식의 위험성을 예측하는 엔드포인트 (인증 필요)
    
    - **formula**: 화학식 문자열 (예: "Al2O3", "H2O")
    - **verbose**: 디버그 정보 출력 여부 (기본값: False)
    
    **인증 필요**: Authorization 헤더에 Bearer 토큰 필요
    
    Returns:
    - **is_risky**: 위험 여부 (True: 위험, False: 안전)
    - **probability_risky**: 위험 확률 (0.0 ~ 1.0)
    - **probability_safe**: 안전 확률 (0.0 ~ 1.0)
    - **prediction**: 예측 결과 문자열 ("위험" 또는 "안전")
    """
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        # 임베딩 추출 (작업 디렉토리를 Safety_Check_Model로 변경하여 경로 문제 해결)
        with torch.no_grad():
            with change_working_dir(SAFETY_MODEL_DIR):
                embedding = get_combined_embedding(
                    formula=request.formula,
                    properties=model_config['properties'],
                    compute_device=str(device),
                    verbose=request.verbose,
                )
            
            # 배치 차원 추가 (1, embedding_dim)
            embedding = embedding.unsqueeze(0).to(device)
            
            # 모델 추론
            logits = model(embedding)
            probs = torch.softmax(logits, dim=1)
            
            # 확률 추출
            # 클래스 0 = 비위험(안전), 클래스 1 = 위험
            prob_safe = probs[0][0].item()  # 클래스 0: 비위험(안전)
            prob_risky = probs[0][1].item()  # 클래스 1: 위험
            
            is_risky = prob_risky > 0.6
            prediction = "위험" if is_risky else "안전"
        
        return SafetyCheckResponse(
            formula=request.formula,
            is_risky=is_risky,
            probability_risky=prob_risky,
            probability_safe=prob_safe,
            prediction=prediction
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/synthesis/answer", response_model=SynthesisAnswerResponse)
async def answer_synthesis_question(
    request: SynthesisQuestionRequest
):
    """
    화학 물질 합성법 질문에 답변하는 엔드포인트 (인증 불필요)
    
    - **question**: 사용자 질문 (예: "NiO 합성법을 단계별로 설명해주세요")
    
    **인증 불필요**: 로그인 없이 사용 가능
    
    Returns:
    - **answer**: LLM이 생성한 답변
    - **context**: RAG 컨텍스트 (합성법 정보)
    - **confidence**: 신뢰도 ("high", "none" 등)
    - **source**: 출처 ("knowledge_graph" 등)
    - **target_material**: 추출된 타겟 물질명
    - **extracted_formulas**: 추출된 화학식 목록
    - **chosen_method_index**: 선택된 합성법 인덱스 (1부터 시작)
    - **chosen_method_label**: 선택된 합성법 라벨
    - **method_count**: 전체 합성법 개수
    - **synthesis_type**: 합성 타입 ("hydrothermal", "precipitation" 등)
    - **synthesis_type_confidence**: 합성 타입 분류 신뢰도
    - **synthesis_type_reason**: 합성 타입 분류 근거
    - **available_materials**: 사용 가능한 물질 목록 (오류 시에만 포함)
    """
    if rag_system is None:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG system is not available. Please check RDF file path and API keys."
        )
    
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question is required"
        )
    
    try:
        result = rag_system.answer_question(request.question.strip())
        
        return SynthesisAnswerResponse(
            answer=result.get("answer", ""),
            context=result.get("context", []),
            confidence=result.get("confidence", "none"),
            source=result.get("source", "none"),
            target_material=result.get("target_material"),
            extracted_formulas=result.get("extracted_formulas"),
            chosen_method_index=result.get("chosen_method_index"),
            chosen_method_label=result.get("chosen_method_label"),
            method_count=result.get("method_count"),
            synthesis_type=result.get("synthesis_type"),
            synthesis_type_confidence=result.get("synthesis_type_confidence"),
            synthesis_type_reason=result.get("synthesis_type_reason"),
            available_materials=result.get("available_materials")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

