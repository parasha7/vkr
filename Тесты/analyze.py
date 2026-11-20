#!/usr/bin/env python3
"""Расчёт статистик по реальным данным сырого CSV. Данные не генерируются."""
import csv
import math
import statistics
import sys
from pathlib import Path

try:
    from scipy import stats
    HAVE_SCIP = True
except ImportError:
    HAVE_SCIP = False


def load(path):
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if not (r.get('code') or '').strip():
                continue
            rows.append(r)
    return rows


def col(rows, name, group=None):
    out = []
    for r in rows:
        if group and r.get('group', '').strip() != group:
            continue
        v = (r.get(name) or '').strip().replace(',', '.')
        if v:
            try:
                out.append(float(v))
            except ValueError:
                pass
    return out


def fmt(x, n=2):
    return 'не рассчитано' if x is None else f'{x:.{n}f}'


def describe(values, label):
    if len(values) < 2:
        print(f'{label}: недостаточно данных (n={len(values)})')
        return None
    m = statistics.mean(values)
    sd = statistics.stdev(values)
    print(f'{label}: n={len(values)}, M={m:.2f}, σ={sd:.2f}, '
          f'медиана={statistics.median(values):.2f}, '
          f'min={min(values):.2f}, max={max(values):.2f}')
    if HAVE_SCIP and len(values) >= 3:
        w, p = stats.shapiro(values)
        print(f'  Шапиро-Уилк: W={w:.3f}, p={p:.4f}')
    else:
        print('  Шапиро-Уилк: не рассчитано')
    return m, sd


def compare(a, b, label):
    if len(a) < 2 or len(b) < 2:
        print(f'{label}: недостаточно данных')
        return
    ma, sa = statistics.mean(a), statistics.stdev(a)
    mb, sb = statistics.mean(b), statistics.stdev(b)
    va, vb = sa ** 2 / len(a), sb ** 2 / len(b)
    se = math.sqrt(va + vb)
    t = (ma - mb) / se if se else None
    df = ((va + vb) ** 2) / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)) if se else None
    sp = math.sqrt(((len(a) - 1) * sa ** 2 + (len(b) - 1) * sb ** 2) / (len(a) + len(b) - 2))
    d = (ma - mb) / sp if sp else None
    if t is None or df is None:
        print(f'{label}: невозможно посчитать t')
        return
    if HAVE_SCIP:
        p = 2 * stats.t.sf(abs(t), df)
        crit = stats.t.ppf(0.975, df)
        lo = (ma - mb) - crit * se
        hi = (ma - mb) + crit * se
        p_str, ci_str = f'{p:.5f}', f'[{lo:.2f}; {hi:.2f}]'
    else:
        p_str = 'не рассчитано (установите scipy)'
        ci_str = 'не рассчитано'
    print(f'{label}: t(Welch)={t:.3f}, df={df:.1f}, p={p_str}, '
          f"Cohen's d={fmt(d, 3)}, 95% CI={ci_str}")


def main():
    if len(sys.argv) < 2:
        print('Использование: python3 analyze.py данные/сырые_данные.csv')
        return
    path = Path(sys.argv[1])
    if not path.exists():
        print(f'Файл не найден: {path}')
        return
    rows = load(path)
    if not rows:
        print('CSV пуст. Сначала проведите тесты и внесите реальные результаты.')
        return
    print(f'Загружено строк: {len(rows)}')
    print('scipy доступен:', HAVE_SCIP)
    for metric, label in [
        ('pre_test', 'Входной тест'),
        ('post_test', 'Итоговый тест'),
        ('motivation_pre', 'Мотивация до'),
        ('motivation_post', 'Мотивация после'),
        ('common_task', 'Обязательная работа'),
    ]:
        print(f'\n=== {label} ===')
        eg = describe(col(rows, metric, 'ЭГ'), 'ЭГ')
        kg = describe(col(rows, metric, 'КГ'), 'КГ')
        if eg and kg:
            compare(col(rows, metric, 'ЭГ'), col(rows, metric, 'КГ'), 'Сравнение ЭГ vs КГ')
    print('\n=== Приросты ===')
    for group in ('ЭГ', 'КГ'):
        pre, post = col(rows, 'pre_test', group), col(rows, 'post_test', group)
        if len(pre) == len(post) and pre:
            delta = [b - a for a, b in zip(pre, post)]
            print(f'{group}: средний прирост = {statistics.mean(delta):+.2f} балла')
    print('\nНапоминание: результаты можно переносить в ВКР только после реального проведения тестов.')


if __name__ == '__main__':
    main()
