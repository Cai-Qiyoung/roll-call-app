from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from database import get_db
from models import Student

router = APIRouter(prefix="/ranking", tags=["ranking"])


def _as_dict(s: Student, rank: int) -> dict:
    return {
        "rank": rank,
        "student_no": s.student_no,
        "name": s.name,
        "major": s.major,
        "score": s.score,
        "roll_count": s.roll_count,
    }


@router.get("/top")
def top_students(n: int = 10, db: Session = Depends(get_db)):
    """积分最高的前 n 名（用于柱形图/折线图可视化）。"""
    students = db.query(Student).order_by(Student.score.desc()).limit(n).all()
    return [_as_dict(s, i + 1) for i, s in enumerate(students)]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    total = len(students)
    return {
        "total_students": total,
        "total_rolls": sum(s.roll_count for s in students),
        "max_score": max((s.score for s in students), default=0),
        "avg_score": round(sum(s.score for s in students) / total, 2) if total else 0,
    }


@router.get("/export")
def export_detail(db: Session = Depends(get_db)):
    """导出积分详单（Excel）：学号、姓名、专业、随机点名次数、总积分。"""
    students = db.query(Student).order_by(Student.score.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "积分详单"
    ws.append(["排名", "学号", "姓名", "专业", "随机点名次数", "总积分"])
    for i, s in enumerate(students):
        ws.append([i + 1, s.student_no, s.name, s.major, s.roll_count, s.score])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=score_detail.xlsx"},
    )