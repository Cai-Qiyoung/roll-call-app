"""点名模块单元测试：权重算法、顺序游标、到场确认、答题计分、转移权。"""

import pytest
from routers import rollcall as rc

from helpers import add_student


def _fake_choices(monkeypatch, return_impl=None):
    """替换 random.choices，捕获传入的 population/weights 并返回指定学生。"""
    captured = {}

    def fake(population, weights=None, k=1):
        captured["population"] = population
        captured["weights"] = weights
        if return_impl is not None:
            return return_impl(population)
        return [population[0]]

    monkeypatch.setattr(rc.random, "choices", fake)
    return captured


# ---------- 随机点名：权重算法 ----------

def test_weight_higher_score_means_lower_probability(client, db, monkeypatch):
    """高积分学生的抽样权重应更低（积分越高越安全）。"""
    add_student(db, "001", score=0)
    add_student(db, "002", score=20)
    captured = _fake_choices(monkeypatch)

    client.post("/rollcall/random")

    assert captured["weights"][0] > captured["weights"][1]


def test_thursday_boosts_score_multiple_of_50(client, db, monkeypatch):
    """疯狂星期四：积分为 50 的倍数的学生权重 x3。"""
    add_student(db, "001", score=50)  # 50 的倍数
    add_student(db, "002", score=60)
    cap_off = _fake_choices(monkeypatch)
    client.post("/rollcall/random", params={"thursday": 0})
    r_off = cap_off["weights"][0] / cap_off["weights"][1]

    cap_on = _fake_choices(monkeypatch)
    client.post("/rollcall/random", params={"thursday": 1})
    r_on = cap_on["weights"][0] / cap_on["weights"][1]

    assert r_on == pytest.approx(r_off * 3)


def test_random_marks_picked_and_grants_transfer_token_every_two(client, db):
    """每被点到 2 次获得 1 次转移权。"""
    add_student(db, "001")
    r1 = client.post("/rollcall/random").json()
    assert r1["roll_count"] == 1 and r1["transfer_tokens"] == 0

    r2 = client.post("/rollcall/random").json()
    assert r2["roll_count"] == 2 and r2["transfer_tokens"] == 1


def test_random_empty_list_returns_404(client, db):
    assert client.post("/rollcall/random").status_code == 404


# ---------- 顺序点名 ----------

def test_sequence_follows_student_no_order(client, db):
    add_student(db, "003")
    add_student(db, "001")
    add_student(db, "002")
    picked = [client.post("/rollcall/sequence").json()["student_no"] for _ in range(3)]
    assert picked == ["001", "002", "003"]


def test_sequence_cursor_wraps_around(client, db):
    add_student(db, "001")
    add_student(db, "002")
    first = client.post("/rollcall/sequence").json()["student_no"]
    client.post("/rollcall/sequence")
    third = client.post("/rollcall/sequence").json()["student_no"]
    assert first == third  # 游标循环回第一位


# ---------- 到场确认 ----------

def test_confirm_attend_adds_one_point(client, db):
    add_student(db, "001")
    res = client.post("/rollcall/confirm", json={"student_no": "001", "attend": True})
    assert res.json()["result"] == "attend"
    assert res.json()["delta"] == 1
    assert res.json()["score"] == 1


def test_confirm_double_event_doubles_point(client, db):
    add_student(db, "001")
    res = client.post(
        "/rollcall/confirm",
        json={"student_no": "001", "attend": True, "event": "double"},
    )
    assert res.json()["delta"] == 2


def test_confirm_absent_no_score(client, db):
    add_student(db, "001")
    res = client.post("/rollcall/confirm", json={"student_no": "001", "attend": False})
    assert res.json()["result"] == "absent"
    assert res.json()["score"] == 0


def test_confirm_with_free_card_escapes(client, db):
    add_student(db, "001", free_card=1)
    res = client.post(
        "/rollcall/confirm",
        json={"student_no": "001", "attend": True, "use_free_card": True},
    )
    assert res.json()["result"] == "escaped"
    assert res.json()["free_card"] == 0
    assert res.json()["score"] == 0


def test_confirm_without_free_card_raises_400(client, db):
    add_student(db, "001")
    res = client.post(
        "/rollcall/confirm",
        json={"student_no": "001", "attend": True, "use_free_card": True},
    )
    assert res.status_code == 400


# ---------- 答题计分 ----------

def test_score_repeat_question_wrong_minus_one(client, db):
    add_student(db, "001")
    res = client.post("/rollcall/score", json={"student_no": "001", "delta": -1})
    assert res.json()["score"] == -1


def test_score_answer_adds_points(client, db):
    add_student(db, "001")
    res = client.post("/rollcall/score", json={"student_no": "001", "delta": 2.5})
    assert res.json()["score"] == 2.5


def test_score_lucky_event_adds_half_point(client, db):
    add_student(db, "001")
    res = client.post(
        "/rollcall/score", json={"student_no": "001", "delta": 2, "event": "lucky"}
    )
    assert res.json()["delta"] == 2.5


def test_score_double_event_and_card_multiply(client, db):
    add_student(db, "001", double_card=2)
    res = client.post(
        "/rollcall/score",
        json={"student_no": "001", "delta": 2, "event": "double", "use_double_card": True},
    )
    assert res.json()["delta"] == 8  # 2 x2(事件) x2(加倍卡)
    assert res.json()["double_card"] == 1


def test_score_without_double_card_raises_400(client, db):
    add_student(db, "001")
    res = client.post(
        "/rollcall/score",
        json={"student_no": "001", "delta": 2, "use_double_card": True},
    )
    assert res.status_code == 400


def test_score_unknown_student_404(client, db):
    assert client.post("/rollcall/score", json={"student_no": "x", "delta": 1}).status_code == 404


# ---------- 点名转移权 ----------

def test_transfer_consumes_token_and_marks_target(client, db):
    a = add_student(db, "001", name="张三", transfer_tokens=1)
    b = add_student(db, "002", name="李四")
    res = client.post(
        "/rollcall/transfer",
        json={"from_student_no": "001", "to_student_no": "002"},
    ).json()

    assert res["from"]["transfer_tokens"] == 0
    assert res["to"]["roll_count"] == 1
    assert res["to"]["transfer_tokens"] == 0  # 才算第 1 次，未满 2 次


def test_transfer_without_token_raises_400(client, db):
    add_student(db, "001")
    add_student(db, "002")
    res = client.post(
        "/rollcall/transfer",
        json={"from_student_no": "001", "to_student_no": "002"},
    )
    assert res.status_code == 400


def test_transfer_to_self_raises_400(client, db):
    add_student(db, "001", transfer_tokens=1)
    res = client.post(
        "/rollcall/transfer",
        json={"from_student_no": "001", "to_student_no": "001"},
    )
    assert res.status_code == 400