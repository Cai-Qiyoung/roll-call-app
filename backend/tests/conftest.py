import sys
from pathlib import Path

# 让测试能 import backend 包（config/database/models/routers 均在 backend 目录下）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  注册 ORM 模型
from database import Base, get_db
from routers import auth, ranking, rollcall, shop, students

# 测试用内存 SQLite：每个用例独立建表/删表，速度快且与开发库完全隔离
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    """每个测试用例独立的数据库会话（含建表/删表，顺序游标随之归零）。"""
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    """独立 FastAPI 应用（不 import main.py，避免触碰开发 MySQL）。"""
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    app.include_router(students.router)
    app.include_router(rollcall.router)
    app.include_router(ranking.router)
    app.include_router(shop.router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c