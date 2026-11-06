"""Explicit airport-code matching; metadata gaps are never silently fabricated."""
from __future__ import annotations

import pandas as pd


def reference_by_code(reference: pd.DataFrame, required_codes=None) -> pd.DataFrame:
    """Return unique BTS-compatible IATA/FAA codes, retaining source identifiers.

    Real OurAirports identifiers are ICAO/internal identifiers. The synthetic
    fixture supplies an explicit iata_code too, so it exercises the same join.
    Local FAA codes fill only rows without an IATA code, never override one.
    """
    out = reference.copy()
    code = out.get('iata_code', pd.Series(pd.NA, index=out.index, dtype='string'))
    code = code.astype('string').str.strip().str.upper().replace('', pd.NA)
    out['_code_priority'] = code.isna().astype('int8')
    if 'local_code' in out:
        code = code.fillna(out['local_code'].astype('string').str.strip().str.upper().replace('', pd.NA))
    # Backwards compatibility for explicitly synthetic three-character fixtures.
    if 'iata_code' not in out and 'ident' in out:
        fallback = out['ident'].astype('string')
        code = code.fillna(fallback.where(fallback.str.fullmatch(r'[A-Z0-9]{3}')))
    out['airport_code'] = code
    # Explicit, source-documented historical aliases; do not guess via K+code.
    from . import config
    aliases = config.ROOT / 'config/airport_aliases.csv'
    if aliases.exists():
        for alias in pd.read_csv(aliases).itertuples():
            if alias.panel_code not in set(out['airport_code'].dropna()):
                matches = out.loc[out['ident'].eq(alias.reference_ident)
                                  | out.get('iata_code', pd.Series('', index=out.index)).eq(alias.alternate_iata)]
                if len(matches) == 1:
                    row = matches.copy()
                    row['airport_code'] = alias.panel_code
                    row['_code_priority'] = 0
                    out = pd.concat([out, row], ignore_index=True)
    out = out.dropna(subset=['airport_code'])
    out = out[out['airport_code'].str.fullmatch(r'[A-Z0-9]{3}')]
    if required_codes is not None:
        out = out[out['airport_code'].isin(required_codes)]
    priority = out.groupby('airport_code')['_code_priority'].transform('min')
    out = out.loc[out['_code_priority'].eq(priority)]
    if out['airport_code'].duplicated().any():
        duplicates = out.loc[out['airport_code'].duplicated(False), 'airport_code'].tolist()
        raise ValueError(f'Ambiguous airport-code mapping: {duplicates}')
    return out.set_index('airport_code')


def attach_metadata(features: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Join one metadata record per airport, keep and report unmatched records."""
    lookup = reference_by_code(reference, features.index)
    columns = ['latitude_deg', 'longitude_deg', 'type', 'municipality', 'name']
    out = features.drop(columns=columns + ['hub_stratum'], errors='ignore').join(
        lookup.reindex(columns=columns), how='left', validate='one_to_one')
    out['metadata_matched'] = (out['latitude_deg'].between(-90,90)
                               & out['longitude_deg'].between(-180,180))
    if len(out) and not out['metadata_matched'].any():
        raise ValueError('No airports matched the reference: check IATA/FAA code mapping')
    # Airport physical type is a proxy, NOT an FAA passenger-enplanement hub class.
    from . import schema
    out['hub_stratum'] = out['type'].map(schema.HUB_STRATUM).astype('float32')
    return out
