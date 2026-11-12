"""Cloud-only password gate and signed persistent device cookies (stdlib only)."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, threading, time
from collections import deque
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

COOKIE='__Host-vedika_session'
DAYS=365
_guard=threading.Lock()
_attempts={}

def required():
    return os.environ.get('VEDIKA_CLOUD')=='1' or os.environ.get('VEDIKA_AUTH_ENABLED')=='1'

def config():
    user=os.environ.get('VEDIKA_AUTH_USERNAME','')
    password_hash=os.environ.get('VEDIKA_PASSWORD_HASH','')
    secret=os.environ.get('VEDIKA_SESSION_SECRET','')
    if not user or not password_hash or len(secret)<32:
        raise RuntimeError('Cloud sign-in is not configured. Set the three authentication environment variables.')
    pieces=password_hash.split('$')
    if len(pieces)!=4 or pieces[0]!='pbkdf2_sha256':raise RuntimeError('Invalid authentication configuration.')
    try:
        iterations=int(pieces[1]);salt=bytes.fromhex(pieces[2]);expected=bytes.fromhex(pieces[3])
        if not 200000<=iterations<=2000000 or len(salt)<16 or len(expected)!=32:raise ValueError()
    except ValueError:raise RuntimeError('Invalid authentication configuration.')
    return user,password_hash,secret,iterations,salt,expected

def make_password_hash(password):
    salt=secrets.token_bytes(16);count=600000
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,count)
    return f'pbkdf2_sha256${count}${salt.hex()}${digest.hex()}'

def valid_credentials(username,password):
    user,_,_,count,salt,expected=config()
    candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,count)
    return hmac.compare_digest(username.encode(),user.encode()) & hmac.compare_digest(candidate,expected)

def _encode(payload):return base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
def _decode(payload):return base64.urlsafe_b64decode(payload+'='*(-len(payload)%4))

def issue_session():
    user,pwh,secret,*_=config();now=int(time.time())
    body=_encode(json.dumps({'u':user,'iat':now,'exp':now+DAYS*86400,'v':hashlib.sha256((user+pwh).encode()).hexdigest()},separators=(',',':')).encode())
    signature=_encode(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest())
    return body+'.'+signature

def valid_session(value):
    if not value or len(value)>2048:return False
    try:
        user,pwh,secret,*_=config();body,signature=value.split('.')
        expected=_encode(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(signature,expected):return False
        payload=json.loads(_decode(body));now=int(time.time())
        return payload.get('u')==user and isinstance(payload.get('exp'),int) and isinstance(payload.get('iat'),int) and payload['iat']<=now+60 and now<payload['exp']<=payload['iat']+DAYS*86400 and payload.get('v')==hashlib.sha256((user+pwh).encode()).hexdigest()
    except (ValueError,TypeError,KeyError,RuntimeError,UnicodeError):return False

def set_session(response):
    response.set_cookie(COOKIE,issue_session(),max_age=DAYS*86400,httponly=True,secure=True,samesite='lax',path='/')

def public_path(path):
    return path in {'/login','/api/health','/api/auth/login','/api/auth/logout','/api/auth/status','/source','/static/login.css','/static/login.js','/static/lotus.svg','/static/icons/lotus-192.png','/static/icons/lotus-512.png','/static/manifest.webmanifest'}

async def gate(request:Request,call_next):
    if not required():return await call_next(request)
    try:config()
    except RuntimeError:
        return JSONResponse({'error':'Cloud login configuration is incomplete. The app is locked until configured.'},status_code=503,headers={'Cache-Control':'no-store'})
    authenticated=valid_session(request.cookies.get(COOKIE))
    request.state.authenticated=authenticated
    if not authenticated and not public_path(request.url.path):
        if (request.url.path.startswith('/api/') or request.url.path=='/openapi.json'):
            return JSONResponse({'error':'Please sign in.','login_url':'/login'},status_code=401,headers={'Cache-Control':'no-store'})
        return RedirectResponse('/login',status_code=303,headers={'Cache-Control':'no-store'})
    response=await call_next(request)
    if authenticated and request.url.path!='/api/auth/logout':set_session(response)
    return response

def limited(key):
    now=time.monotonic()
    with _guard:
        if len(_attempts)>10000:
            for old in list(_attempts):
                if not _attempts[old] or now-_attempts[old][-1]>900:_attempts.pop(old,None)
        entries=_attempts.setdefault(key,deque())
        while entries and now-entries[0]>900:entries.popleft()
        if len(entries)>=10:return True
        entries.append(now)
        return False

def clear_attempts(key):
    with _guard:_attempts.pop(key,None)
