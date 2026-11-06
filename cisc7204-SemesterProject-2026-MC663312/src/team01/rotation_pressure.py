"""UTC, whole-aircraft sequence analysis of hypothetical turnaround pressure.

This is not a causal allocation of realised arrival delay. Positive pressure can
exceed the next flight's arrival delay because of recovery en route. Missing
source legs and historical changes in airport timezone references remain limits.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import config, features, io

TIMEZONE_URL = 'https://raw.githubusercontent.com/mborsetti/airportsdata/main/airportsdata/airports.csv'


def timezone_reference() -> dict[str, str]:
    path = config.ROOT / 'data/raw/reference/airport_timezones.csv'
    if not path.exists():
        io.download(TIMEZONE_URL, path)
    ref = pd.read_csv(path, keep_default_na=False)
    # FAA LID is needed for a few reporting codes different from IATA.
    mapping = {}
    for key in ['lid', 'iata']:
        subset = ref[ref[key].str.fullmatch(r'[A-Z0-9]{3}') & ref['tz'].ne('')]
        for code, rows in subset.groupby(key):
            zones = rows['tz'].unique()
            if len(zones) == 1:
                mapping[code] = zones[0]
    aliases = config.ROOT / 'config/airport_aliases.csv'
    if aliases.exists():
        for alias in pd.read_csv(aliases).itertuples():
            matches = ref.loc[ref['icao'].eq(alias.reference_ident) | ref['iata'].eq(alias.alternate_iata), 'tz'].unique()
            if alias.panel_code not in mapping and len(matches) == 1:
                mapping[alias.panel_code] = matches[0]
    return mapping


def add_utc_times(frame: pd.DataFrame, zones: dict[str, str]) -> pd.DataFrame:
    """Reconstruct times from source fields; uncertain DST times become missing."""
    out = frame.copy()
    hhmm = out['crs_dep_time']
    valid_clock = hhmm.notna() & hhmm.between(0, 2400) & ((hhmm % 100) < 60)
    local = (pd.to_datetime(out['flight_date'])
             + pd.to_timedelta(hhmm // 100, unit='h')
             + pd.to_timedelta(hhmm % 100, unit='m')).where(valid_clock)
    timezone = out['origin'].astype('string').map(zones)
    utc = pd.Series(pd.NaT, index=out.index, dtype='datetime64[ns, UTC]')
    for zone in timezone.dropna().unique():
        mask = timezone.eq(zone).fillna(False)
        utc.loc[mask] = local.loc[mask].dt.tz_localize(
            zone, ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC')
    elapsed = out['crs_elapsed'].where(out['crs_elapsed'] > 0)
    out['sched_dep_utc'] = utc
    out['sched_arr_utc'] = utc + pd.to_timedelta(elapsed, unit='m')
    out['actual_arr_utc'] = out['sched_arr_utc'] + pd.to_timedelta(out['arr_delay'], unit='m')
    out['utc_status'] = np.select(
        [~valid_clock, timezone.isna(), utc.isna(), elapsed.isna()],
        ['invalid_clock','unknown_origin_timezone','ambiguous_or_nonexistent_local_time','missing_or_nonpositive_elapsed'],
        default='usable_schedule')
    out['dep_hour'] = ((hhmm // 100) % 24).where(valid_clock).astype('Int8')
    return out


def analyse_file(path: Path, tails: int = 256, min_turnaround: int = 25) -> dict:
    """Sample aircraft uniformly, then retain ALL source records for those tails.

    Scan only the required Parquet columns. Cancelled/diverted records stay in
    the ordering so they cannot be silently skipped when choosing a predecessor.
    """
    if tails < 1:
        raise ValueError('At least one aircraft must be sampled')
    file = pq.ParquetFile(path)
    codes = pc.unique(pq.read_table(path, columns=['tail_number'])['tail_number']).to_pylist()
    codes = sorted(str(c) for c in codes if c is not None and str(c).strip())
    rng = np.random.default_rng(config.seed())
    selected = sorted(rng.choice(codes, min(tails, len(codes)), replace=False).tolist())
    columns = ['tail_number', 'flight_date', 'crs_dep_time', 'crs_elapsed', 'arr_delay',
               'origin', 'dest', 'carrier', 'cancelled', 'diverted']
    chunks = []
    for batch in file.iter_batches(batch_size=250_000, columns=columns):
        table = pa.Table.from_batches([batch])
        values = pc.cast(table['tail_number'], pa.string())
        chosen = table.filter(pc.is_in(values, value_set=pa.array(selected)))
        if len(chosen):
            chunks.append(chosen)
    sample = pa.concat_tables(chunks).to_pandas().reset_index(drop=True)
    sample = add_utc_times(sample, timezone_reference())
    results = {}
    for turn in [15, min_turnaround, 45]:
        legs = features.leg_sequence(sample, min_turnaround_min=turn)
        results[str(turn)] = features.cascade_summary(legs, sample)
        if turn == min_turnaround:
            selected_legs=legs.loc[legs['is_rotation'] & legs['arr_delay'].notna()].copy()
            selected_legs['positive_arrival_min']=selected_legs['arr_delay'].clip(lower=0)
            by_aircraft=selected_legs.groupby('tail_number',observed=True).agg(
                pressure_min=('inherited_min','sum'),positive_arrival_min=('positive_arrival_min','sum'),
                rotations=('arr_delay','size')).reindex(selected,fill_value=0)
    summary = results[str(min_turnaround)]
    pick=rng.integers(0,len(selected),size=(1000,len(selected)))
    numerator=by_aircraft['pressure_min'].to_numpy()[pick].sum(axis=1)
    denominator=by_aircraft['positive_arrival_min'].to_numpy()[pick].sum(axis=1)
    ratios=numerator[denominator>0]/denominator[denominator>0]
    summary['uncertainty']={
        'method':'Aircraft-cluster percentile bootstrap; 1000 draws; zero-rotation sampled tails retained',
        'ratio_ci_low':float(np.quantile(ratios,.025)),
        'ratio_ci_high':float(np.quantile(ratios,.975)),
        'limits':'Conditional on sampled aircraft, observed source records, timezone reference and the minimum-turn assumption; not a causal confidence interval or correction for missing legs',
    }
    summary['by_aircraft']=by_aircraft.reset_index()
    summary.update({
        'status': 'exploratory_turnaround_pressure_not_arrival_attribution',
        'sampling_unit': 'aircraft tail; every source record retained',
        'aircraft_sampled': len(selected), 'aircraft_available': len(codes),
        'sample_rows': len(sample), 'utc_valid_rows': int(sample['sched_dep_utc'].notna().sum()),
        'missing_utc_rows': int(sample['sched_dep_utc'].isna().sum()),
        'utc_status_counts': sample['utc_status'].value_counts().to_dict(),
        'selected_tails': selected, 'seed': config.seed(),
        'min_turnaround_minutes': min_turnaround,
        'time_basis': 'UTC sequence; hour summaries use origin-local scheduled hour',
        'sensitivity': {key: {k: v for k, v in value.items() if k not in ('hourly', 'by_airport')}
                        for key, value in results.items()},
        'interpretation': 'Pressure is an assumed minimum-turnaround shortfall, not minutes of realised arrival delay. Ratios may exceed one.',
    })
    return summary
