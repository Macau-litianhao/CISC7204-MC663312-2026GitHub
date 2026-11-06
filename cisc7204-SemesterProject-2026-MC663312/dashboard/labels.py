"""Human-readable names without changing analytical carrier or airport codes."""
from functools import lru_cache
import csv
from team01 import config


@lru_cache(maxsize=1)
def _names():
    result={}
    for kind in ['airport','carrier']:
        path=config.ROOT/f'config/{kind}_display.csv'
        with path.open(encoding='utf-8',newline='') as handle:
            result[kind]={row['code']:row for row in csv.DictReader(handle)}
    return result


def carrier_label(code):
    name=_names()['carrier'].get(str(code),{}).get('name')
    return f'{name} ({code})' if name else str(code)


def airport_label(code):
    row=_names()['airport'].get(str(code),{})
    if not row:
        return str(code)
    return f"{row['city']} · {row['name']} ({code})"


def airport_short(code):
    city=_names()['airport'].get(str(code),{}).get('city','').split(',')[0]
    return f'{city} ({code})' if city else str(code)
