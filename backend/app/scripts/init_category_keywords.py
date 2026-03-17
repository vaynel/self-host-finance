"""
카테고리 자동분류 기본 키워드(init/seed) 스크립트.

실행 예시:
  - 모든 사용자에 기본 키워드 삽입(중복은 건너뜀)
    python -m app.scripts.init_category_keywords --all-users

  - 특정 사용자만
    python -m app.scripts.init_category_keywords --user-id usr_xxx

옵션:
  --dry-run  : 실제 저장하지 않고 출력만
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
from typing import Iterable
import uuid

from sqlalchemy import func

# SQLAlchemy 엔진이 import 시 생성되며(env=development면 echo=True), 그 전에 로그 레벨을 낮춰 noisy output을 줄입니다.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.category_keyword import CategoryKeyword

# 엔진이 생성된 후 echo가 True로 강제될 수 있어, 스크립트에서는 조용히 실행되도록 끕니다.
engine.echo = False


@dataclass(frozen=True)
class SeedItem:
    keyword: str
    category: str
    type: str = "expense"  # income | expense | transfer | all
    priority: str = "normal"  # high | normal | low


DEFAULT_SEEDS: list[SeedItem] = [
    # 식료품/마트
    SeedItem("이마트", "식료품", "expense", "normal"),
    SeedItem("홈플러스", "식료품", "expense", "normal"),
    SeedItem("롯데마트", "식료품", "expense", "normal"),
    SeedItem("코스트코", "식료품", "expense", "normal"),
    SeedItem("GS더프레시", "식료품", "expense", "low"),
    # 편의점
    SeedItem("CU", "편의점", "expense", "low"),
    SeedItem("GS25", "편의점", "expense", "low"),
    SeedItem("세븐일레븐", "편의점", "expense", "low"),
    # 카페
    SeedItem("스타벅스", "카페", "expense", "normal"),
    SeedItem("투썸", "카페", "expense", "normal"),
    SeedItem("메가커피", "카페", "expense", "low"),
    SeedItem("컴포즈", "카페", "expense", "low"),
    # 배달
    SeedItem("배달의민족", "배달", "expense", "normal"),
    SeedItem("요기요", "배달", "expense", "normal"),
    SeedItem("쿠팡이츠", "배달", "expense", "normal"),
    # 교통
    SeedItem("카카오T", "교통", "expense", "normal"),
    SeedItem("택시", "교통", "expense", "low"),
    SeedItem("지하철", "교통", "expense", "low"),
    SeedItem("버스", "교통", "expense", "low"),
    # 쇼핑/커머스
    SeedItem("쿠팡", "쇼핑", "expense", "normal"),
    SeedItem("네이버페이", "쇼핑", "expense", "normal"),
    SeedItem("11번가", "쇼핑", "expense", "low"),
    SeedItem("G마켓", "쇼핑", "expense", "low"),
    SeedItem("옥션", "쇼핑", "expense", "low"),
    # 구독
    SeedItem("넷플릭스", "구독", "expense", "normal"),
    SeedItem("유튜브", "구독", "expense", "normal"),
    SeedItem("멜론", "구독", "expense", "low"),
    SeedItem("스포티파이", "구독", "expense", "low"),
]


def iter_target_user_ids(db, user_id: str | None, all_users: bool) -> Iterable[str]:
    if user_id:
        return [user_id]
    if all_users:
        return [u[0] for u in db.query(User.id).all()]
    raise SystemExit("오류: --user-id 또는 --all-users 중 하나는 필요합니다.")


def upsert_keywords(db, user_id: str, seeds: list[SeedItem], dry_run: bool) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    for s in seeds:
        kw_norm = s.keyword.strip()
        if not kw_norm:
            continue

        exists = (
            db.query(CategoryKeyword.id)
            .filter(
                CategoryKeyword.user_id == user_id,
                func.lower(CategoryKeyword.keyword) == func.lower(kw_norm),
            )
            .first()
        )
        if exists:
            skipped += 1
            continue

        if dry_run:
            inserted += 1
            continue

        new_id = f"ckw_{uuid.uuid4().hex[:12]}"
        db.add(
            CategoryKeyword(
                id=new_id,
                user_id=user_id,
                keyword=kw_norm,
                category=s.category,
                type=s.type,
                priority=s.priority,
            )
        )
        inserted += 1

    if not dry_run:
        db.commit()

    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="FinFlow 카테고리 자동분류 기본 키워드 초기화(시드).")
    parser.add_argument("--user-id", dest="user_id", help="대상 user_id (예: usr_xxx)")
    parser.add_argument("--all-users", action="store_true", help="모든 사용자에 적용")
    parser.add_argument("--dry-run", action="store_true", help="DB에 저장하지 않고 결과만 출력")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        targets = list(iter_target_user_ids(db, args.user_id, args.all_users))
        if not targets:
            print("대상 사용자가 없습니다.")
            return

        total_ins = 0
        total_skip = 0
        for uid in targets:
            ins, skip = upsert_keywords(db, uid, DEFAULT_SEEDS, dry_run=args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"[user={uid}] inserted={ins} skipped(existing)={skip} dry_run={args.dry_run}")

        print(f"[done] users={len(targets)} inserted={total_ins} skipped={total_skip} dry_run={args.dry_run}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

