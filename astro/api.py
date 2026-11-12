"""Stateless local/cloud API: birth details and PDF bytes are never persisted."""
from __future__ import annotations
import json
import os
import math
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
LOCK = threading.RLock()
app = FastAPI(title='Vedika', version='2.0.0', docs_url='/api/docs', redoc_url=None)

class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=100)
    gender: str = Field(default='unspecified', max_length=40)
    date: str
    time: str
    timezone: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-89.99, le=89.99)
    longitude: float = Field(ge=-180, le=180)
    place: str = Field(min_length=1, max_length=300)
    time_accuracy: Literal['exact', 'approximate'] = 'exact'

    @field_validator('date')
    @classmethod
    def validate_date(cls, value):
        parsed = date.fromisoformat(value)
        if value != parsed.isoformat() or parsed < date(1900, 1, 1) or parsed.year > 2100:
            raise ValueError('Birth date must be an ISO date between 1900 and 2100; the resolved birth instant cannot be in the future.')
        return value

    @field_validator('time')
    @classmethod
    def validate_time(cls, value):
        import re
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
            raise ValueError('Birth time is required in HH:MM 24-hour format.')
        return value

class ChartRequest(BaseModel):
    profile: Profile

class PairRequest(BaseModel):
    person_a: Profile
    person_b: Profile

class WindowRequest(PairRequest):
    start_date: date
    end_date: date
    timezone: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-89.99, le=89.99, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    place: str = Field(min_length=1, max_length=300)

class InsightRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile: Profile
    as_of: date | None = None
    horizon_months: int = Field(default=24, ge=1, le=60)


def insight_arguments(req: InsightRequest):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    profile = req.profile.model_dump()
    if req.as_of is None:
        try:
            as_of = datetime.now(ZoneInfo(profile['timezone'])).date().isoformat()
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('A valid IANA timezone is required for the review date.')
    else:
        as_of = req.as_of.isoformat()
    return profile, as_of, req.horizon_months

class ReportRequest(InsightRequest):
    section: Literal['personal', 'love', 'career', 'health', 'compatibility']
    person_b: Profile | None = None
    relationship_status: Literal['considering','married'] = 'considering'

class PDFRequest(ReportRequest):
    language: Literal['en','hi','mr'] = 'en'


def make_report(req: ReportRequest):
    from .reports import build_report
    profile, as_of, months = insight_arguments(req)
    if req.section == 'compatibility' and req.person_b is None:
        raise ValueError('Two complete birth profiles are required for compatibility.')
    return build_report(req.section, profile, as_of, months,
                        person_b=req.person_b.model_dump() if req.person_b else None,
                        relationship_status=req.relationship_status)

@app.middleware('http')
async def local_guard(request: Request, call_next):
    host = request.url.hostname
    cloud_mode = os.environ.get('VEDIKA_CLOUD') == '1'
    if not cloud_mode and host not in ('localhost', '127.0.0.1', 'testserver'):
        return JSONResponse({'error': 'Only local access is enabled.', 'code':'LOCAL_ONLY'}, status_code=403)
    origin = request.headers.get('origin')
    if origin:
        parsed = urlparse(origin)
        # Protect against hostile websites submitting local profile mutations.
        if parsed.scheme not in ('http', 'https') or parsed.netloc != request.headers.get('host'):
            return JSONResponse({'error':'Cross-origin access is disabled.', 'code':'ORIGIN_DENIED'}, status_code=403)
    if request.method in ('POST','PUT','PATCH'):
        if 'application/json' not in request.headers.get('content-type',''):
            return JSONResponse({'error':'Send application/json.', 'code':'JSON_REQUIRED'}, status_code=415)
        # Enforce the limit even when Content-Length is omitted.
        body = await request.body()
        if len(body) > 100_000:
            return JSONResponse({'error':'Request is too large.', 'code':'REQUEST_TOO_LARGE'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

from . import auth
app.middleware('http')(auth.gate)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=512)

@app.get('/login')
def login_page(request: Request):
    if not auth.required() or auth.valid_session(request.cookies.get(auth.COOKIE)):
        return RedirectResponse('/',status_code=303)
    return FileResponse(ROOT/'static'/'login.html',headers={'Cache-Control':'no-store'})

@app.post('/api/auth/login')
def login_action(req: LoginRequest, request: Request):
    if not auth.required():return {'authenticated':True}
    key=request.client.host if request.client else 'unknown'
    if auth.limited(key):
        return JSONResponse({'error':'Too many attempts. Please wait 15 minutes and try again.'},status_code=429,headers={'Retry-After':'900'})
    if not auth.valid_credentials(req.username,req.password):
        return JSONResponse({'error':'Incorrect username or password.'},status_code=401)
    auth.clear_attempts(key)
    response=JSONResponse({'authenticated':True})
    auth.set_session(response)
    return response

@app.get('/api/auth/status')
def auth_status(request: Request):
    return {'authenticated':not auth.required() or auth.valid_session(request.cookies.get(auth.COOKIE))}

@app.post('/api/auth/logout')
def logout_action():
    response=JSONResponse({'authenticated':False})
    response.delete_cookie(auth.COOKIE,path='/',secure=True,httponly=True,samesite='lax')
    return response

@app.get('/source')
def source_code():
    url=os.environ.get('VEDIKA_SOURCE_URL','')
    if url.startswith('https://github.com/'):
        return RedirectResponse(url,status_code=303)
    return FileResponse(ROOT/'LICENSE',media_type='text/plain')

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    errors = [{ 'field': '.'.join(str(p) for p in item['loc']), 'message': item['msg']} for item in exc.errors()]
    return JSONResponse({'error':'Please check the entered details.', 'code':'INVALID_INPUT','fields':errors}, status_code=422)

@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({'error':str(exc), 'code':'CALCULATION_INPUT'}, status_code=422)

@app.exception_handler(RuntimeError)
async def calculation_error(request, exc):
    return JSONResponse({'error':str(exc), 'code':'CALCULATION_UNAVAILABLE'}, status_code=503)

@app.get('/api/health')
def health():
    files = ['sepl_18.se1','semo_18.se1']
    result={'app':'vedika','status':'ok','version':'2.0.0','instance_id':os.environ.get('VEDIKA_INSTANCE_ID',''),'ephemeris_ready':all((ROOT/'data'/'ephe'/f).is_file() for f in files),'places_ready':(ROOT/'data'/'places.sqlite3').is_file(),'offline':True,'deployment_mode':'cloud' if os.environ.get('VEDIKA_CLOUD')=='1' else 'local','personal_data_storage':False}
    result['authentication_required']=auth.required()
    if auth.required():result.pop('instance_id',None)
    return result

@app.get('/api/places')
def places(q: str = '', country: str = 'IN'):
    from .places import search_places
    if len(q.strip()) < 2:
        return []
    if len(q) > 100 or len(country) > 3:
        raise ValueError('Use a search of 2–100 characters and an ISO country code.')
    return search_places(q, country.upper())

@app.post('/api/chart')
def chart_api(req: ChartRequest):
    from .engine import chart
    with LOCK:
        return chart(req.profile.model_dump())

@app.post('/api/match')
def match_api(req: PairRequest):
    from .matching import match
    with LOCK:
        return match(req.person_a.model_dump(), req.person_b.model_dump())

@app.post('/api/windows')
def window_api(req: WindowRequest):
    from .timing import candidate_dates
    with LOCK:
        return candidate_dates(req.model_dump(mode='json'))

@app.post('/api/dosha-report')
def dosha_report_api(req: InsightRequest):
    from .interpretation import dosha_report
    with LOCK:
        return dosha_report(*insight_arguments(req))

@app.post('/api/career-report')
def career_report_api(req: InsightRequest):
    from .interpretation import career_report
    with LOCK:
        return career_report(*insight_arguments(req))

@app.post('/api/personal-marriage')
def personal_marriage_api(req: InsightRequest):
    from .marriage import personal_marriage_report
    with LOCK:
        return personal_marriage_report(*insight_arguments(req))

@app.post('/api/report')
def report_api(req: ReportRequest):
    with LOCK:
        return make_report(req)

@app.post('/api/report/pdf')
def report_pdf_api(req: PDFRequest):
    from .pdf_report import render_pdf
    with LOCK:
        report = make_report(req)
        payload = render_pdf(report, req.language)
    return Response(payload, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="Vedika-{req.section}-{report["as_of"]}.pdf"',
        'Cache-Control': 'no-store',
    })

@app.get('/')
def index():
    return FileResponse(ROOT/'static'/'index.html')

app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
