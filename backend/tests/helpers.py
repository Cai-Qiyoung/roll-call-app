from models import Student


def add_student(db, student_no, name=None, major="软件工程", score=0.0, **kw):
    """快捷构造一名学生并刷新到数据库。"""
    s = Student(
        student_no=student_no,
        name=name or f"学生{student_no}",
        major=major,
        score=score,
        **kw,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s