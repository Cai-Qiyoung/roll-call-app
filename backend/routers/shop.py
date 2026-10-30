from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RollRecord, Student
from schemas import ExchangeIn

router = APIRouter(prefix="/shop", tags=["shop"])

ITEMS = {
    "free_card": {"code": "free_card", "name": "免点券", "cost": 30, "desc": "被点名时可直接豁免本轮"},
    "double_card": {"code": "double_card", "name": "加倍卡", "cost": 20, "desc": "回答问题得分 x2"},
}


@router.get("/items")
def list_items():
    return list(ITEMS.values())


def _student_out(s: Student) -> dict:
    return {
        "student_no": s.student_no,
        "name": s.name,
        "major": s.major,
        "score": s.score,
        "roll_count": s.roll_count,
        "transfer_tokens": s.transfer_tokens,
        "free_card": s.free_card,
        "double_card": s.double_card,
    }


@router.get("/{student_no}")
def student_wallet(student_no: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_no == student_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return _student_out(student)


@router.post("/exchange")
def exchange(payload: ExchangeIn, db: Session = Depends(get_db)):
    """积分兑换道具：免点券 30 分、加倍卡 20 分。"""
    item = ITEMS.get(payload.item_code)
    if not item:
        raise HTTPException(status_code=400, detail="商品不存在")

    student = db.query(Student).filter(Student.student_no == payload.student_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.score < item["cost"]:
        raise HTTPException(status_code=400, detail=f"积分不足（需要 {item['cost']} 分）")

    student.score -= item["cost"]
    if payload.item_code == "free_card":
        student.free_card += 1
    else:
        student.double_card += 1

    db.add(
        RollRecord(
            student_id=student.id,
            kind="exchange",
            delta=-item["cost"],
            remark=f"兑换 {item['name']}",
        )
    )
    db.commit()
    db.refresh(student)
    return _student_out(student)