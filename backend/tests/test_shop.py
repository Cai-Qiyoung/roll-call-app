"""积分商店单元测试：商品列表、兑换扣分、余额校验。"""

from models import RollRecord

from helpers import add_student


def test_items_list(client, db):
    items = client.get("/shop/items").json()
    codes = {i["code"] for i in items}
    assert codes == {"free_card", "double_card"}


def test_exchange_free_card_deducts_score(client, db):
    add_student(db, "001", score=40)
    res = client.post(
        "/shop/exchange", json={"student_no": "001", "item_code": "free_card"}
    ).json()

    assert res["score"] == 10  # 40 - 30
    assert res["free_card"] == 1


def test_exchange_records_roll_record(client, db):
    add_student(db, "001", score=30)
    client.post("/shop/exchange", json={"student_no": "001", "item_code": "free_card"})

    record = db.query(RollRecord).one()
    assert record.kind == "exchange"
    assert record.delta == -30


def test_exchange_insufficient_score_returns_400(client, db):
    add_student(db, "001", score=10)
    res = client.post(
        "/shop/exchange", json={"student_no": "001", "item_code": "free_card"}
    )
    assert res.status_code == 400


def test_exchange_unknown_item_returns_400(client, db):
    add_student(db, "001", score=999)
    res = client.post(
        "/shop/exchange", json={"student_no": "001", "item_code": "ghost_item"}
    )
    assert res.status_code == 400


def test_wallet_unknown_student_404(client, db):
    assert client.get("/shop/xxxx").status_code == 404