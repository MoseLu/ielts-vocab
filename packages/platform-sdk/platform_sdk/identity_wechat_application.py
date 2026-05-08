from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from platform_sdk.identity_repository_adapter import auth_repository
from platform_sdk.identity_session_support import check_rate_limit, reset_rate_limit

WECHAT_API_BASE = 'https://api.weixin.qq.com'


class WeChatLoginError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _clean(value) -> str:
    return str(value or '').strip()


def _wechat_timeout(app) -> int:
    return int(app.config.get('WECHAT_HTTP_TIMEOUT_SECONDS') or 5)


def _wechat_credentials(app) -> tuple[str, str]:
    return (
        _clean(app.config.get('WECHAT_MOBILE_APP_ID')),
        _clean(app.config.get('WECHAT_MOBILE_APP_SECRET')),
    )


def _wechat_get(path: str, params: dict[str, str], timeout: int) -> dict:
    url = f'{WECHAT_API_BASE}{path}?{urlencode(params)}'
    try:
        with urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        raise WeChatLoginError('微信登录服务暂时不可用') from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise WeChatLoginError('微信登录服务暂时不可用') from exc


def _raise_for_wechat_error(payload: dict) -> None:
    errcode = payload.get('errcode')
    if errcode in (None, 0):
        return
    message = _clean(payload.get('errmsg')) or '微信授权失败'
    if errcode in {40029, 40163, 42003}:
        raise WeChatLoginError('微信授权已失效，请重新授权', status_code=401)
    raise WeChatLoginError(f'微信授权失败：{message}')


def exchange_wechat_code(app, code: str) -> dict:
    appid, secret = _wechat_credentials(app)
    payload = _wechat_get(
        '/sns/oauth2/access_token',
        {
            'appid': appid,
            'secret': secret,
            'code': code,
            'grant_type': 'authorization_code',
        },
        _wechat_timeout(app),
    )
    _raise_for_wechat_error(payload)
    return payload


def fetch_wechat_userinfo(app, access_token: str, openid: str) -> dict:
    payload = _wechat_get(
        '/sns/userinfo',
        {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN',
        },
        _wechat_timeout(app),
    )
    _raise_for_wechat_error(payload)
    return payload


def _identity_from_wechat_payload(app, token_payload: dict) -> dict[str, str]:
    access_token = _clean(token_payload.get('access_token'))
    openid = _clean(token_payload.get('openid'))
    profile: dict = {}
    if access_token and openid:
        try:
            profile = fetch_wechat_userinfo(app, access_token, openid)
        except WeChatLoginError:
            app.logger.info('WeChat userinfo fetch failed; continuing with token payload only')
    return {
        'openid': _clean(profile.get('openid')) or openid,
        'unionid': _clean(profile.get('unionid')) or _clean(token_payload.get('unionid')),
        'nickname': _clean(profile.get('nickname')),
        'avatar_url': _clean(profile.get('headimgurl')),
    }


def perform_mobile_wechat_login(app, flask_request, data: dict) -> tuple[dict, int, int | None]:
    code = _clean(data.get('code'))
    if not code:
        return {'error': '缺少微信授权 code'}, 400, None
    if not app.config.get('WECHAT_LOGIN_ENABLED'):
        return {'error': '微信登录未启用'}, 503, None
    appid, secret = _wechat_credentials(app)
    if not appid or not secret:
        return {'error': '微信登录服务未配置'}, 503, None

    ip = flask_request.remote_addr or '0.0.0.0'
    allowed, wait = check_rate_limit(app, ip, purpose='wechat_login', subject='wechat')
    if not allowed:
        return {'error': f'微信登录尝试过于频繁，请 {wait} 秒后再试', 'retry_after': wait}, 429, None

    try:
        identity = _identity_from_wechat_payload(app, exchange_wechat_code(app, code))
    except WeChatLoginError as exc:
        return {'error': str(exc)}, exc.status_code, None

    if not identity['openid']:
        return {'error': '微信授权结果缺少 openid'}, 502, None

    user, created = auth_repository.create_or_update_wechat_user(**identity)
    if user is None:
        return {'error': '微信账号绑定的用户不存在'}, 401, None
    reset_rate_limit(ip, purpose='wechat_login', subject='wechat')
    return {
        'message': '登录成功',
        'user': user.to_dict(),
        'access_expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'is_new_user': created,
    }, 200, user.id
