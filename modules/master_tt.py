import json
import os
import pandas as pd

TT_FILE = 'data/master_tt.json'

DEFAULT_TT = [
    ('HCU', 'HCU', 3, True),
    ('ICU', 'ICU', 3, True),
    ('NICU', 'NICU', 3, True),
    ('PICU', 'PICU', 1, True),
    ('Isolasi-ICU', 'Isolasi-ICU', 3, True),
    ('Perina Level 2', 'Perina', 5, True),
    ('Perina Level 1 Room', 'Perina', 0, False),
    ('Sakinah-1', 'Isolasi Normal', 2, True),
    ('Sakinah-2', 'Isolasi Normal', 5, True),
    ('Firdaus-1', 'VIP', 1, True),
    ('Firdaus-2', 'VIP', 1, True),
    *[(f'Ar Rahmah-{i}', 'Kelas 1', 2, True) for i in range(1, 16)],
    ('Safa-1', 'Kelas 2', 2, True),
    ('Safa-2', 'Kelas 2', 2, True),
    ('Safa-3', 'Kelas 2', 3, True),
    *[(f'Marwah-{i}', 'Kelas 3', 4, True) for i in range(1, 10)],
    ('Transit IGD', 'Transit IGD', 0, False),
]

def _ensure_dir():
    os.makedirs('data', exist_ok=True)

def load_master_tt() -> pd.DataFrame:
    _ensure_dir()
    if os.path.exists(TT_FILE):
        with open(TT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    df = pd.DataFrame(DEFAULT_TT, columns=['ruangan', 'kelas', 'jumlah_tt', 'dihitung_bor'])
    save_master_tt(df)
    return df

def save_master_tt(df: pd.DataFrame):
    _ensure_dir()
    df.to_json(TT_FILE, orient='records', indent=2, force_ascii=False)

def total_tt_dihitung(df: pd.DataFrame) -> int:
    return int(df[df['dihitung_bor'] == True]['jumlah_tt'].sum())
