from pydantic import BaseModel


class StudentOut(BaseModel):
    student_no: str
    name: str
    major: str = ""
    score: float = 0.0
    roll_count: int = 0
    transfer_tokens: int = 0
    free_card: int = 0
    double_card: int = 0

    model_config = {"from_attributes": True}


class LoginIn(BaseModel):
    code: str


class LoginOut(BaseModel):
    token: str
    openid: str


class ConfirmIn(BaseModel):
    """到场确认（可携带随机事件与免点券）"""

    student_no: str
    attend: bool = True
    use_free_card: bool = False
    event: str = "none"


class TransferIn(BaseModel):
    from_student_no: str
    to_student_no: str


class ScoreIn(BaseModel):
    """答题加减分（可携带事件加成与加倍卡）"""

    student_no: str
    delta: float = 0.0
    question: str = ""
    event: str = "none"
    use_double_card: bool = False


class ExchangeIn(BaseModel):
    student_no: str
    item_code: str