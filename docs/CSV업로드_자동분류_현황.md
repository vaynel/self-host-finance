# CSV 업로드 및 자동 분류 기능 현황

> 작성일: 2026-03-17  
> 최종 수정일: 2026-03-17 (중복 거래 감지 및 미리보기 기능 추가)

---

## 📋 목차

1. [현재 구현 상태](#현재-구현-상태)
2. [구현된 기능](#구현된-기능)
3. [구현되지 않은 기능](#구현되지-않은-기능)
4. [구현 필요 사항](#구현-필요-사항)
5. [CSV/Excel 파일 형식 지원](#csvexcel-파일-형식-지원)
6. [카테고리 키워드 관리](#카테고리-키워드-관리)

---

## 현재 구현 상태

### ✅ 구현된 부분

#### 1. Backend API (완료)

**파일 위치:**
- `backend/app/routers/upload.py` - 업로드 엔드포인트
- `backend/app/services/upload_service.py` - 파싱 및 임포트 로직
- `backend/app/services/smart_upload_parser.py` - 스마트 파서 (새로 추가)
- `backend/app/services/category_classifier.py` - 자동 분류 로직 (새로 추가)

**구현 내용:**
- ✅ `POST /v1/upload/transactions` 엔드포인트 구현
- ✅ **스마트 CSV/Excel 파싱** - 다양한 은행 형식 자동 감지
- ✅ **자동 컬럼 매핑** - 헤더 자동 인식 및 매핑
- ✅ **Type 자동 판단** - 금액 부호 및 키워드 기반
- ✅ **Category 자동 분류** - DB 기반 키워드 매칭
- ✅ 거래 내역 일괄 임포트
- ✅ 파일 형식 자동 감지 (CSV/XLSX)
- ✅ 인코딩 처리 (UTF-8-SIG 지원)
- ✅ 에러 처리 및 결과 반환 (imported, skipped, errors)

**API 엔드포인트:**
```python
POST /v1/upload/transactions
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (필수) - CSV 또는 XLSX 파일
- accountId: str (필수) - 계좌 ID
- format: Optional[str] - 파일 형식 (csv, xlsx, xls)
- skipDuplicates: Optional[bool] - 중복 거래 건너뛰기 (기본값: true)
- toleranceDays: Optional[int] - 날짜 허용 오차 일수 (기본값: 0)

Response:
{
  "success": true,
  "data": {
    "imported": 10,  // 성공적으로 임포트된 건수
    "skipped": 2,    // 건너뛴 건수 (중복 포함)
    "duplicates": 2, // 중복 거래 건수
    "errors": [      // 에러 목록
      {"row": 5, "message": "에러 메시지"}
    ],
    "column_mapping": {  // 감지된 컬럼 매핑 정보
      "date": 0,
      "description": 1,
      "amount": 2,
      ...
    }
  }
}
```

#### 2. 스마트 파서 기능 (완료)

**파일:** `backend/app/services/smart_upload_parser.py`

**주요 기능:**
- ✅ **유연한 컬럼 매핑** - 다양한 헤더명 자동 인식
  - 날짜: "날짜", "date", "거래일자", "거래일", "일자", "일시", "거래시각"
  - 설명: "내역", "거래내역", "description", "적요", "거래적요", "내용", "메모", "비고"
  - 금액: "금액", "amount", "거래금액", "입금", "출금", "수입", "지출", "변동금액"
  - 잔액: "잔액", "balance", "거래후잔액", "잔고"
  - 기타: "구분", "카테고리", "계좌", "메모" 등

- ✅ **다양한 날짜 형식 지원**
  - YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
  - MM/DD/YYYY, DD/MM/YYYY
  - YYYYMMDD (연속 형식)
  - Excel 날짜 셀 자동 변환

- ✅ **다양한 금액 형식 지원**
  - 콤마 포함: "1,000,000"
  - 통화 기호: "₩1,000,000", "$1,000"
  - 음수 표기: "(1,000)", "-1,000"
  - 공백 제거 및 정제

- ✅ **Excel 모든 행 읽기**
  - openpyxl을 사용하여 모든 시트의 모든 행 읽기
  - 빈 행 자동 건너뛰기
  - 데이터 타입 자동 변환

#### 3. 자동 분류 기능 (완료)

**파일:** `backend/app/services/category_classifier.py`

**Type 자동 판단:**
- 금액 부호 기반: 음수 → expense, 양수 → income (키워드 확인 후)
- Description 키워드 기반:
  - 수입: "급여", "월급", "배당", "이자", "환급", "보너스", "수입", "입금", "적립"
  - 지출: "결제", "출금", "이체", "수수료", "지출", "승인"

**Category 자동 분류:**
- DB 기반 키워드 매칭 (사용자별 관리)
- 우선순위 기반 매칭 (high > normal > low)
- 금액 범위 기반 보조 분류 (50만원 이상 → 주거)

#### 4. 중복 거래 감지 (완료)

**파일 위치:**
- `backend/app/services/duplicate_detector.py` - 중복 감지 로직
- `backend/app/services/upload_service.py` - 중복 체크 통합

**구현 내용:**
- ✅ 날짜, 금액, 설명, 계좌 기반 중복 체크
- ✅ 중복 거래 건너뛰기 옵션 (기본값: 활성화)
- ✅ 날짜 허용 오차 설정 (tolerance_days)
- ✅ 중복 거래 수 반환

**중복 판단 기준:**
1. 같은 사용자 (user_id)
2. 같은 날짜 (또는 tolerance_days 범위 내)
3. 같은 금액 (정확히 일치, 소수점 2자리)
4. 같은 계좌 (account)
5. 같은 설명 (대소문자 무시, 공백 정규화, 부분 일치 포함)

**API 파라미터:**
- `skipDuplicates`: 중복 거래 건너뛰기 여부 (기본값: true)
- `toleranceDays`: 날짜 허용 오차 일수 (기본값: 0 = 정확히 일치)

**응답 형식:**
```json
{
  "success": true,
  "data": {
    "imported": 10,
    "skipped": 3,
    "duplicates": 2,
    "errors": []
  }
}
```

#### 5. 카테고리 키워드 관리 (완료)

**DB 스키마:**
- `category_keywords` 테이블 생성
- 사용자별 키워드 관리
- 카테고리별 키워드 그룹화
- 우선순위 설정 (high, normal, low)

**API 엔드포인트:**
- `GET /v1/category-keywords` - 키워드 목록 조회
- `POST /v1/category-keywords` - 키워드 추가
- `PUT /v1/category-keywords/{id}` - 키워드 수정
- `DELETE /v1/category-keywords/{id}` - 키워드 삭제
- `GET /v1/category-keywords/categories` - 카테고리 목록 조회

**Frontend UI:**
- 설정 페이지에 키워드 관리 섹션 추가
- 카테고리별 키워드 표시
- 키워드 추가/삭제 기능
- 우선순위 설정

#### 6. 데이터베이스 저장 (완료)

- ✅ 거래 내역 생성 (`create_transaction` 함수)
- ✅ 사용자별 거래 내역 저장
- ✅ 트랜잭션 단위 처리 (에러 발생 시 해당 행만 건너뛰기)
- ✅ 카테고리 키워드 저장 및 조회

---

### ❌ 구현되지 않은 부분

#### 1. Frontend 업로드 UI 연결 (✅ 완료)

**구현 내용:**
- ✅ 파일 선택 기능 (클릭 및 드래그 앤 드롭)
- ✅ 업로드 진행 상태 표시
- ✅ 업로드 결과 상세 표시 (성공/실패/중복)
- ✅ 계좌 선택 드롭다운
- ✅ 중복 거래 감지 옵션
- ✅ 업로드 이력 표시

**미구현 기능:**
- 업로드 전 미리보기 (우선순위 3)

#### 2. 중복 거래 감지 (✅ 완료)

**구현 내용:**
- ✅ 날짜, 금액, 설명 기반 중복 체크
- ✅ 중복 거래 건너뛰기 옵션 (기본값: 활성화)
- ✅ 중복 거래 수 표시
- ✅ 날짜 허용 오차 설정 (tolerance_days)

**파일 위치:**
- `backend/app/services/duplicate_detector.py` - 중복 감지 로직
- `backend/app/services/upload_service.py` - 중복 체크 통합
- `backend/app/routers/upload.py` - API 옵션 추가

**중복 판단 기준:**
- 같은 사용자 (user_id)
- 같은 날짜 (또는 tolerance_days 범위 내)
- 같은 금액 (정확히 일치)
- 같은 계좌 (account)
- 같은 설명 (대소문자 무시, 공백 정규화, 부분 일치 포함)

#### 2. 업로드 전 미리보기 (✅ 완료)

**구현 내용:**
- ✅ 파일 파싱 후 미리보기 화면
- ✅ 자동 분류 결과 확인
- ✅ 데이터 수정 기능 (인라인 편집)
- ⚠️ 일괄 수정 기능 (부분 구현 - 개별 수정만 가능)

**파일 위치:**
- `backend/app/routers/upload.py` - `/upload/preview` API 엔드포인트
- `frontend/src/pages/Upload.tsx` - 미리보기 UI

**기능:**
- 파일 선택 후 "미리보기" 버튼 클릭
- 파싱된 거래 내역을 테이블로 표시
- 각 필드 클릭 시 인라인 편집 가능
- 날짜, 설명, 금액, 구분, 카테고리 수정 가능

#### 3. 다양한 은행 형식 사전 정의 (부분 구현)

**현재 상태:**
- 일반적인 컬럼명 패턴만 지원
- 특정 은행 형식 사전 정의 없음

**필요한 기능:**
- 주요 은행별 CSV 형식 사전 정의
- 카드사별 승인내역 형식 지원
- 증권사 거래내역 형식 지원

---

## 구현 필요 사항

### 우선순위 1: Frontend 업로드 UI 완성 (✅ 완료)

**구현 내용:**
1. ✅ 파일 선택 기능 구현
2. ✅ `uploadApi.uploadTransactions` API 호출 연결
3. ✅ 계좌 선택 드롭다운 추가
4. ✅ 업로드 진행 상태 표시
5. ✅ 업로드 결과 표시 (성공/실패 건수, 에러 목록, 중복 거래)
6. ✅ 드래그 앤 드롭 지원
7. ✅ 업로드 이력 표시

**파일 수정:**
- `frontend/src/pages/Upload.tsx` - 완전히 재작성 완료

---

### 우선순위 2: 중복 거래 감지 (✅ 완료)

**구현 내용:**
1. ✅ 날짜, 금액, 설명 기반 중복 체크
2. ✅ 중복 거래 건너뛰기 옵션
3. ✅ 중복 거래 수 표시

**API 파라미터:**
- `skipDuplicates`: 중복 거래 건너뛰기 여부 (기본값: true)
- `toleranceDays`: 날짜 허용 오차 일수 (기본값: 0)

**응답 형식:**
```json
{
  "success": true,
  "data": {
    "imported": 10,
    "skipped": 3,
    "duplicates": 2,
    "errors": []
  }
}
```

---

### 우선순위 3: 업로드 전 미리보기 (✅ 완료)

**구현 내용:**
1. ✅ 파일 파싱 후 미리보기 화면
2. ✅ 자동 분류 결과 확인
3. ✅ 데이터 수정 기능 (인라인 편집)
4. ⚠️ 일괄 수정 기능 (부분 구현)

**API 엔드포인트:**
```
POST /v1/upload/preview
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (필수)
- format: Optional[str]
- accountId: Optional[str] (계좌 선택 시 자동 분류에 사용)

Response:
{
  "success": true,
  "data": {
    "rows": [
      {
        "row": 1,
        "date": "2024-01-01",
        "description": "거래 내용",
        "amount": 10000,
        "type": "expense",
        "category": "식비",
        "account": "계좌명",
        "memo": ""
      },
      ...
    ],
    "column_mapping": {...},
    "total": 10
  }
}
```

---

## CSV/Excel 파일 형식 지원

### 현재 지원하는 형식

**자동 감지 컬럼:**
- **날짜**: "날짜", "date", "거래일자", "거래일", "일자", "일시", "거래시각"
- **설명**: "내역", "거래내역", "description", "적요", "거래적요", "내용", "메모", "비고"
- **금액**: "금액", "amount", "거래금액", "입금", "출금", "수입", "지출", "변동금액"
- **잔액**: "잔액", "balance", "거래후잔액", "잔고" (선택)
- **구분**: "구분", "type", "유형", "거래구분", "입출금" (선택)
- **카테고리**: "카테고리", "category", "분류", "항목" (선택)
- **계좌**: "계좌", "account", "계좌번호", "계좌명", "은행" (선택)
- **메모**: "메모", "memo", "비고", "참고", "기타" (선택)

**날짜 형식:**
- YYYY-MM-DD
- YYYY/MM/DD
- YYYY.MM.DD
- MM/DD/YYYY
- DD/MM/YYYY
- YYYYMMDD

**금액 형식:**
- 콤마 포함: "1,000,000"
- 통화 기호: "₩1,000,000", "$1,000"
- 음수 표기: "(1,000)", "-1,000"

**최소 필수 컬럼:**
- 날짜 (date)
- 설명 (description)

**자동 처리:**
- Type: 금액 부호 및 키워드 기반 자동 판단
- Category: DB 키워드 기반 자동 분류
- Account: 업로드 시 선택한 계좌 사용

### 예시 CSV 형식

**형식 1: 표준 형식**
```csv
날짜,거래내역,금액,구분,카테고리,계좌
2026-03-17,스타벅스,6500,지출,카페,신한카드
2026-03-16,월급,4500000,수입,급여,국민은행
```

**형식 2: 은행 거래내역**
```csv
거래일자,적요,입금,출금,잔액
2026-03-17,스타벅스,0,6500,1000000
2026-03-16,급여이체,4500000,0,1006500
```

**형식 3: 카드 승인내역**
```csv
승인일시,가맹점명,승인금액,카드번호
2026-03-17,스타벅스,6500,1234-****-****-5678
```

---

## 카테고리 키워드 관리

### DB 스키마

**테이블:** `category_keywords`

```sql
CREATE TABLE category_keywords (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',  -- high, normal, low
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX ix_category_keywords_user_id ON category_keywords(user_id);
CREATE INDEX ix_category_keywords_category ON category_keywords(category);
CREATE INDEX ix_category_keywords_keyword ON category_keywords(keyword);
CREATE INDEX ix_category_keywords_user_category ON category_keywords(user_id, category);
```

### API 사용법

**키워드 목록 조회:**
```bash
GET /v1/category-keywords
GET /v1/category-keywords?category=식료품
```

**키워드 추가:**
```bash
POST /v1/category-keywords
Content-Type: application/json

{
  "category": "식료품",
  "keyword": "마켓컬리",
  "priority": "high"
}
```

**키워드 수정:**
```bash
PUT /v1/category-keywords/{keyword_id}
Content-Type: application/json

{
  "category": "식료품",
  "keyword": "마켓컬리",
  "priority": "normal"
}
```

**키워드 삭제:**
```bash
DELETE /v1/category-keywords/{keyword_id}
```

**카테고리 목록 조회:**
```bash
GET /v1/category-keywords/categories
```

### Frontend UI

**위치:** 설정 페이지 (`/settings`)

**기능:**
- 카테고리별 키워드 목록 표시
- 키워드 추가 (카테고리, 키워드, 우선순위)
- 키워드 삭제
- 우선순위 표시 (high는 빨간색 배지)

### 기본 카테고리

- 식료품
- 카페
- 교통
- 쇼핑
- 구독
- 주거
- 의료
- 교육
- 운동
- 배달
- 편의점
- 기타

### 키워드 우선순위

- **high**: 가장 우선적으로 매칭 (예: 특정 가맹점명)
- **normal**: 일반적인 매칭 (기본값)
- **low**: 낮은 우선순위 (일반적인 키워드)

---

## 구현 체크리스트

### Backend
- [x] CSV 파싱 기능
- [x] XLSX 파싱 기능
- [x] 스마트 컬럼 매핑
- [x] 거래 내역 임포트 기능
- [x] Type 자동 판단 기능
- [x] Category 자동 분류 기능 (DB 기반)
- [x] 카테고리 키워드 관리 API
- [x] 중복 거래 감지 기능
- [x] 업로드 전 미리보기 기능
- [ ] Account 자동 매칭 기능
- [ ] 다양한 CSV 형식 사전 정의
- [ ] 데이터 정제 기능

### Frontend
- [x] 파일 선택 기능
- [x] 파일 드래그 앤 드롭
- [x] 업로드 진행 상태 표시
- [x] 계좌 선택 드롭다운
- [x] 업로드 결과 표시
- [x] 중복 거래 감지 옵션
- [x] 중복 거래 결과 표시
- [x] 카테고리 키워드 관리 UI
- [x] 업로드 전 미리보기
- [x] 자동 분류 결과 확인/수정

---

## 참고 파일

### Backend
- `backend/app/routers/upload.py` - 업로드 API 엔드포인트
- `backend/app/services/upload_service.py` - 파싱 및 임포트 로직
- `backend/app/services/smart_upload_parser.py` - 스마트 파서
- `backend/app/services/category_classifier.py` - 자동 분류 로직
- `backend/app/services/duplicate_detector.py` - 중복 거래 감지 로직
- `backend/app/routers/category_keywords.py` - 키워드 관리 API
- `backend/app/models/category_keyword.py` - 키워드 모델
- `backend/app/services/transaction_service.py` - 거래 내역 생성
- `backend/alembic/versions/a2c9b09ce264_add_category_keywords_table.py` - 키워드 테이블 마이그레이션

### Frontend
- `frontend/src/pages/Upload.tsx` - 업로드 페이지 (완전 구현)
- `frontend/src/pages/SettingsPage.tsx` - 설정 페이지 (키워드 관리)
- `frontend/src/lib/api.ts` - 업로드 및 키워드 API 클라이언트

---

## 다음 단계

1. ✅ **완료:** Frontend 업로드 UI 연결 (우선순위 1)
2. ✅ **완료:** 중복 거래 감지 (우선순위 2)
3. ✅ **완료:** 업로드 전 미리보기 (우선순위 3)
4. **다음 작업:** 수정된 미리보기 데이터로 업로드 기능
5. **장기 작업:** 다양한 은행 형식 사전 정의

---

## 기술 스택

- **Backend**: FastAPI, SQLAlchemy, openpyxl, csv
- **Frontend**: React, TypeScript, TanStack Query
- **Database**: PostgreSQL
- **파일 형식**: CSV, XLSX
