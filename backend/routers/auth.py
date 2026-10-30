import httpx
from fastapi import APIRouter, HTTPException

from config import settings
from schemas import LoginIn, LoginOut

router = APIRouter(tags=["auth"])

WX_JSCODE2SESSION = "https://api.weixin.qq.com/sns/jscode2session"


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn):
    """微信小程序登录：用 code 换取 openid，参考 fastapi-wechat-login 的实现方式。"""
    params = {
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
        "js_code": payload.code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(WX_JSCODE2SESSION, params=params)
    data = resp.json()

    if "openid" not in data:
        raise HTTPException(status_code=401, detail=f"微信登录失败: {data.get('errmsg')}")

    openid = data["openid"]
    # TODO: 生产环境应签发 JWT（用 TOKEN_SECRET 签名），此处以 openid 作为临时 token
    return LoginOut(token=openid, openid=openid)