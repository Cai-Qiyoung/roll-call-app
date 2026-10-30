from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    """学生名单"""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_no = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(64), nullable=False)
    major = Column(String(128), default="")
    score = Column(Float, default=0.0)  # 总积分
    roll_count = Column(Integer, default=0)  # 被点名次数
    total_rolled = Column(Integer, default=0)  # 累计被抽中次数（转移权计数用）
    transfer_tokens = Column(Integer, default=0)  # 点名转移权（可转移次数）
    free_card = Column(Integer, default=0)  # 免点券（积分商店兑换）
    double_card = Column(Integer, default=0)  # 加倍卡（积分商店兑换）


class RollRecord(Base):
    """点名/答题/兑换流水，用于积分明细"""

    __tablename__ = "roll_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    mode = Column(String(16), default="random")  # random | sequence
    kind = Column(String(16), default="roll")  # attend | absent | answer | transfer | exchange | free_escape
    question = Column(String(256), default="")
    delta = Column(Float, default=0.0)
    event = Column(String(16), default="")  # double | lucky
    remark = Column(String(256), default="")
    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student")


class AppState(Base):
    """键值状态（如顺序点名的游标）"""

    __tablename__ = "app_state"

    key = Column(String(64), primary_key=True)
    value = Column(String(255), default="")