from fastapi import FastAPI

import models  # noqa: F401  # 注册模型
from database import Base, engine
from routers import auth, ranking, rollcall, shop, students

# 首次启动建表（生产环境建议改用 Alembic 迁移）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="课堂随机点名系统")

app.include_router(auth.router, prefix="/auth")
app.include_router(students.router)
app.include_router(rollcall.router)
app.include_router(ranking.router)
app.include_router(shop.router)


@app.get("/")
def root():
    return {"message": "课堂随机点名系统后端已启动"}