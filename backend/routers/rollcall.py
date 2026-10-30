import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AppState, RollRecord, Student
from schemas import ConfirmIn, ScoreIn, TransferIn

router = APIRouter(prefix="/rollcall", tags=["rollcall"])


def _pick_event() -> str:
    r = random.random()
    if r < 0.08:
        return "double"
    if r < 0.16:
        return "lucky"
    return "none"


def _get_state(db: Session, key: str, default: str = "0") -> AppState:
    st = db.get(AppState, key)
    if st is None:
        st = AppState(key=key, value=default)
        db.add(st)
        db.commit()
    return st


def _out(s: Student, **extra) -> dict:
    d = {
        "student_no": s.student_no,
        "name": s.name,
        "major": s.major,
        "score": s.score,
        "roll_count": s.roll_count,
        "transfer_tokens": s.transfer_tokens,
        "free_card": s.free_card,
        "double_card": s.double_card,
    }
    d.update(extra)
    return d


def _mark_picked(s: Student):
    """被抽中：累计点名次数 +1，每两次获得一次转移权。"""
    s.total_rolled += 1
    s.roll_count += 1
    if s.total_rolled % 2 == 0:
        s.transfer_tokens += 1


@router.post("/random")
def random_roll(thursday: bool = False, db: Session = Depends(get_db)):
    """随机点名：积分越高概率越低；疯狂星期四时积分为 50 的倍数的同学概率 x3。"""
    students = db.query(Student).all()
    if not students:
        raise HTTPException(status_code=404, detail="名单为空")

    thursday = thursday or datetime.now().weekday() == 3
    weights = []
    for s in students:
        w = 1.0 / (1.0 + max(s.score, 0.0))
        if thursday and s.score > 0 and s.score % 50 == 0:
            w *= 3.0
        weights.append(w)

    picked = random.choices(students, weights=weights, k=1)[0]
    boosted = thursday and picked.score > 0 and picked.score % 50 == 0
    _mark_picked(picked)
    event = _pick_event()
    db.commit()
    db.refresh(picked)
    return _out(picked, event=event, thursday=thursday, boosted=boosted)


@router.post("/sequence")
def sequence_roll(db: Session = Depends(get_db)):
    """按学号顺序点名（游标持久化在数据库）。"""
    students = db.query(Student).order_by(Student.student_no).all()
    if not students:
        raise HTTPException(status_code=404, detail="名单为空")

    state = _get_state(db, "seq_index")
    idx = int(state.value or 0) % len(students)
    state.value = str(idx + 1)

    picked = students[idx]
    _mark_picked(picked)
    event = _pick_event()
    db.commit()
    db.refresh(picked)
    return _out(picked, event=event, thursday=False, boosted=False)


@router.post("/confirm")
def confirm_roll(payload: ConfirmIn, db: Session = Depends(get_db)):
    """点名后的确认：到场 +1（双倍事件 x2）/ 缺席不加分 / 使用免点券豁免。"""
    student = (
        db.query(Student).filter(Student.student_no == payload.student_no).first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    if not payload.attend:
        db.add(
            RollRecord(
                student_id=student.id,
                kind="absent",
                delta=0,
                remark=f"{student.name} 缺席",
            )
        )
        db.commit()
        db.refresh(student)
        return _out(student, result="absent", delta=0)

    if payload.use_free_card:
        if student.free_card <= 0:
            raise HTTPException(status_code=400, detail="没有免点券")
        student.free_card -= 1
        db.add(
            RollRecord(
                student_id=student.id,
                kind="free_escape",
                delta=0,
                remark=f"{student.name} 使用免点券豁免本轮",
            )
        )
        db.commit()
        db.refresh(student)
        return _out(student, result="escaped", delta=0)

    delta = 1.0
    if payload.event == "double":
        delta *= 2
    student.score += delta
    db.add(
        RollRecord(
            student_id=student.id,
            kind="attend",
            delta=delta,
            event=payload.event,
            remark=f"{student.name} 到场",
        )
    )
    db.commit()
    db.refresh(student)
    return _out(student, result="attend", delta=delta)


@router.post("/transfer")
def transfer_roll(payload: TransferIn, db: Session = Depends(get_db)):
    """点名转移权：被点同学消耗 1 次转移权，把本次点名转给另一位同学。"""
    a = db.query(Student).filter(Student.student_no == payload.from_student_no).first()
    b = db.query(Student).filter(Student.student_no == payload.to_student_no).first()
    if not a or not b:
        raise HTTPException(status_code=404, detail="学生不存在")
    if a.transfer_tokens <= 0:
        raise HTTPException(status_code=400, detail="该同学没有转移权")
    if a.id == b.id:
        raise HTTPException(status_code=400, detail="不能转移给自己")

    a.transfer_tokens -= 1
    _mark_picked(b)
    db.add(
        RollRecord(
            student_id=a.id,
            kind="transfer",
            delta=0,
            remark=f"{a.name} 将点名转移给 {b.name}",
        )
    )
    db.commit()
    db.refresh(a)
    db.refresh(b)
    return {"from": _out(a), "to": _out(b)}


@router.post("/score")
def answer_score(payload: ScoreIn, db: Session = Depends(get_db)):
    """答题加减分：重复提问正确 +0.5 / 错误 -1，回答正确 +0.5~3；
    事件加成：double 得分 x2；lucky 正分额外 +0.5；可用加倍卡再 x2。"""
    student = (
        db.query(Student).filter(Student.student_no == payload.student_no).first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    delta = payload.delta
    remark = payload.question or "答题"

    if payload.event == "double" and delta != 0:
        delta *= 2
        remark += "（双倍事件）"
    if payload.event == "lucky" and delta > 0:
        delta += 0.5
        remark += "（幸运星+0.5）"
    if payload.use_double_card:
        if student.double_card <= 0:
            raise HTTPException(status_code=400, detail="没有加倍卡")
        student.double_card -= 1
        delta *= 2
        remark += "（加倍卡x2）"

    student.score += delta
    db.add(
        RollRecord(
            student_id=student.id,
            kind="answer",
            question=payload.question,
            delta=delta,
            event=payload.event,
            remark=remark,
        )
    )
    db.commit()
    db.refresh(student)
    return _out(student, delta=delta)