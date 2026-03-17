## CSV/Excel 업로드: LLM 기반 카테고리 자동추가 + 자동분류

### 목표

파일 업로드(미리보기/실제 임포트) 시 카테고리 자동 분류를 다음 정책으로 수행합니다.

- **이미 등록된 카테고리면 LLM에 질의하지 않음**
- **등록되지 않았거나(또는 미분류)면 LLM에 질의**
  - LLM이 기존 카테고리 목록 중 하나를 선택하면 그 카테고리로 분류
  - LLM이 새로운 카테고리를 제안하면 DB에 **새 카테고리를 자동 등록**한 뒤 그 카테고리로 분류

### “등록된 카테고리” 기준

다음 3가지를 합쳐 “등록된 카테고리 목록”을 구성합니다.

- DB 테이블 `categories`에 저장된 사용자 카테고리
- `category_keywords`에 존재하는 `category` 값들(키워드 관리 UI로 만든 카테고리)
- 기본 카테고리(하드코딩): `식료품, 카페, 교통, 쇼핑, 구독, 주거, 의료, 교육, 운동, 배달, 편의점, 기타`

### 동작 흐름 (업로드/미리보기 공통)

1. **파일 파싱**
2. **type 자동 감지** (`income/expense`)
3. **category 자동 분류**
   - (A) row에 category가 있고 등록된 카테고리면 그대로 사용
   - (B) 키워드 기반 분류 시도(`category_keywords`)
   - (C) 그래도 확정 못하면 LLM(Groq) 질의 → 결과 category 적용
     - 새 카테고리면 `categories` 테이블에 자동 추가

### DB 변경점

- 새 테이블: `categories`
  - 컬럼: `id`, `user_id`, `name`, `created_at`, `updated_at`
  - 제약: `(user_id, name)` 유니크

### 관련 코드

- 카테고리 레지스트리: `backend/app/services/category_registry.py`
- 업로드 시 LLM 보강: `backend/app/services/llm_category_enricher.py`
- 업로드 라우터 적용: `backend/app/routers/upload.py`
- 마이그레이션: `backend/alembic/versions/9c1b2f5b7a12_add_categories_table.py`

### 환경 변수

LLM 사용을 위해 Groq 키가 필요합니다.

- `GROQ_API_KEY`: Groq API Key
- `GROQ_BASE_URL`: 기본값 `https://api.groq.com/openai/v1`
- `GROQ_MODEL`: 기본값 `llama3-8b-8192`

키가 없으면 LLM 분류는 자동으로 `"기타"`로 떨어지며(실패 안전), 서비스는 계속 동작합니다.

