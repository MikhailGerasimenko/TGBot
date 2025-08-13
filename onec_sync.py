import csv
import json
import os
import re
from typing import List, Dict
from redis_client import redis_client

UNICODE_SPACES = "\u00A0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u202F\u205F\u3000"

async def load_employees_from_file(file_path: str) -> List[Dict]:
    if not os.path.exists(file_path):
        return []
    _, ext = os.path.splitext(file_path.lower())
    if ext == '.csv':
        return await _load_from_csv(file_path)
    if ext == '.json':
        return await _load_from_json(file_path)
    if ext == '.txt':
        return await _load_from_txt(file_path)
    return []

async def _load_from_csv(file_path: str) -> List[Dict]:
    employees: List[Dict] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            employees.append({
                'employee_id': row.get('employee_id') or row.get('id') or row.get('tabnum'),
                'full_name': row.get('full_name') or row.get('fio'),
                'department': row.get('department') or row.get('dept') or '',
                'position': row.get('position') or row.get('title') or ''
            })
    return [e for e in employees if e.get('employee_id') and e.get('full_name')]

async def _load_from_json(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    employees: List[Dict] = []
    if isinstance(data, list):
        for row in data:
            employees.append({
                'employee_id': row.get('employee_id') or row.get('id') or row.get('tabnum'),
                'full_name': row.get('full_name') or row.get('fio'),
                'department': row.get('department') or row.get('dept') or '',
                'position': row.get('position') or row.get('title') or ''
            })
    return [e for e in employees if e.get('employee_id') and e.get('full_name')]

async def _load_from_txt(file_path: str) -> List[Dict]:
    employees: List[Dict] = []
    # Разрешаем табельному буквы/цифры/дефис, минимум одна цифра
    tab_re = re.compile(r"^[0-9A-Za-zА-Яа-яЁё\-]+$")
    trans_table = str.maketrans({c: ' ' for c in UNICODE_SPACES})
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.rstrip('\n\r')
            if not line.strip():
                continue
            # Пропускаем шапки/служебные строки
            lower = line.lower()
            if lower.startswith('запрос:') or ('ссылка' in lower and 'код' in lower):
                continue
            # Нормализуем нестандартные пробелы
            line = line.translate(trans_table)
            line = re.sub(r"\t+", " ", line)
            line = re.sub(r"\s{2,}", "  ", line)  # схлопываем до двух пробелов минимум
            parts = line.strip().rsplit(' ', 1) if ' ' in line else [line]
            if len(parts) != 2:
                # пробуем по любым пробелам
                parts = re.split(r"\s+", line.strip())
                if len(parts) < 2:
                    continue
                name = ' '.join(parts[:-1])
                tab = parts[-1]
            else:
                name, tab = parts[0].strip(), parts[1].strip()
            if not name or not tab:
                continue
            if not tab_re.match(tab) or not any(ch.isdigit() for ch in tab):
                # если последний токен не похож на табельный — пропускаем
                continue
            employees.append({
                'employee_id': tab,
                'full_name': name,
                'department': '',
                'position': ''
            })
    return employees

async def sync_onec_export_to_redis(file_path: str) -> int:
    employees = await load_employees_from_file(file_path)
    if not employees:
        return 0
    pipe = redis_client.pipeline()
    for emp in employees:
        pipe.hset('employees_cache', emp['employee_id'], json.dumps(emp, ensure_ascii=False))
    await pipe.execute()
    return len(employees) 