"""Offline birthplace lookup. All queries are parameterized and read-only."""
from __future__ import annotations
from pathlib import Path
import re
import sqlite3

DATABASE = Path(__file__).resolve().parents[1] / 'data' / 'places.sqlite3'


def _label(row: dict) -> str:
    parts = []
    for item in [row['name'], row['district'], row['state'], row['country']]:
        if item and item.casefold() not in [p.casefold() for p in parts]:
            parts.append(item)
    text = ', '.join(parts)
    if row['postal_code']:
        text += ' · PIN ' + row['postal_code']
    return text


def search_places(q: str, country: str = 'IN', limit: int = 30) -> list[dict]:
    """Search locality, district, state, country, alternate name or India PIN.

    `country=''` searches worldwide cities plus India postal localities.
    A PIN may contain many localities; each is returned as a separate option.
    Coordinates belong to the named place and must be confirmed by the user.
    """
    q = (q or '').strip()
    if not 2 <= len(q) <= 100:
        return []
    country = (country or '').strip().upper()
    if country in {'ALL', 'WORLD', '*'}:
        country = ''
    if country and not re.fullmatch(r'[A-Z]{2}', country):
        raise ValueError('Country must be a two-letter ISO country code or blank for worldwide.')
    tokens = re.findall(r'[^\W_]+', q, flags=re.UNICODE)
    if not tokens:
        return []
    limit = min(max(int(limit), 1), 50)
    if not DATABASE.is_file():
        raise RuntimeError('Offline place database is missing. Restore data/places.sqlite3 or enter confirmed coordinates manually.')
    with sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        if re.fullmatch(r'\d{6}', q):
            sql = 'SELECT * FROM places WHERE postal_code=?'
            args = [q]
            if country:
                sql += ' AND country_code=?'
                args.append(country)
            sql += ' ORDER BY name COLLATE NOCASE LIMIT ?'
            args.append(limit)
        else:
            match = ' AND '.join('"' + token.replace('"', '""') + '"*' for token in tokens)
            sql = '''SELECT p.* FROM places_fts f JOIN places p ON p.rowid=f.rowid
                     WHERE places_fts MATCH ?'''
            args = [match]
            if country:
                sql += ' AND p.country_code=?'
                args.append(country)
            sql += ''' ORDER BY CASE WHEN lower(p.name)=lower(?) THEN 0 ELSE 1 END,
                       CASE WHEN p.kind='city' THEN 0 ELSE 1 END,
                       p.population DESC, bm25(places_fts, 7.0, 2.0, 2.0, 1.0, 6.0, 0.5) LIMIT ?'''
            args.extend([q, limit])
        records = [dict(row) for row in con.execute(sql, args)]
    result = []
    for row in records:
        result.append({key: row[key] for key in (
            'id', 'name', 'district', 'state', 'country', 'country_code',
            'latitude', 'longitude', 'timezone', 'postal_code')})
        result[-1]['label'] = _label(row)
    return result
