"""Audit current-reference coverage for every source origin/destination code."""
from pathlib import Path
import sys
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from team01 import airports,config,io,models,rotation_pressure


def main():
    counts=[]
    for field in ['origin','dest']:
        values=pc.value_counts(pq.read_table(config.flights_file(),columns=[field])[field]).to_pylist()
        counts.append({row['values']:row['counts'] for row in values})
    origins,destinations=counts
    codes=sorted(set(origins)|set(destinations))
    reference=airports.reference_by_code(io.load_airports(),codes)
    zones=rotation_pressure.timezone_reference()
    audit=pd.DataFrame([{'airport_code':code,'origin_records':origins.get(code,0),
        'destination_records':destinations.get(code,0),
        'current_active_reference_match':code in reference.index,'timezone_known':code in zones}
        for code in codes])
    audit.to_csv(config.TABLE_DIR/'airport_reference_coverage.csv',index=False)
    models.save_metrics({'source_airport_codes':len(codes),
        'active_metadata_matches':int(audit.current_active_reference_match.sum()),
        'timezone_known':int(audit.timezone_known.sum()),
        'missing_active_metadata':audit.loc[~audit.current_active_reference_match,'airport_code'].tolist(),
        'missing_timezones':audit.loc[~audit.timezone_known,'airport_code'].tolist(),
        'scope':'All source origin/destination records, including cancelled/diverted. Metadata lookup retains large/medium/small airport types; excludes seaplane bases and closed facilities.',
        'interpretation':'Current reference coverage is not a complete historical register. Gaps are flagged rather than assigned invented coordinates or timezones.'},'airport_reference_coverage')


if __name__=='__main__':main()
