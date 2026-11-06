"""Content-addressed provenance for empirical and synthetic result sets."""
from functools import lru_cache
from pathlib import Path
import hashlib,json
from . import config

@lru_cache(maxsize=32)
def _digest(path,size,mtime):
    value=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()

def file_digest(path):
    path=Path(path);stat=path.stat()
    return _digest(str(path.resolve()),stat.st_size,stat.st_mtime_ns)

def signature():
    source=config.flights_file()
    if not source.exists():raise FileNotFoundError(source)
    registry=config.ROOT/"config/reference_snapshots.json"
    if config.mode()=="full" and registry.exists():
        for item in json.loads(registry.read_text(encoding="utf-8"))["references"]:
            path=config.ROOT/item["path"]
            if not path.exists() or file_digest(path)!=item["sha256"]:
                raise ValueError(f"Reference snapshot mismatch: {item['path']}; restore the pinned snapshot or explicitly review/update the registry and rebuild all outputs")
    references={}
    for path in [config.airports_file(),config.ROOT/'config/airport_aliases.csv',config.ROOT/'data/raw/reference/airport_timezones.csv']:
        if path.exists():references[path.name]=file_digest(path)
    return {'mode':config.mode(),'source_sha256':file_digest(source),
            'settings_sha256':file_digest(config.CONFIG_FILE),'references':references,
            'protocol':'audit-corrected-v0.5'}

def check(payload):
    if payload.get('run_signature')!=signature():
        raise ValueError('Stale/mixed-mode result: rebuild from the current source/config/reference before use')
    for relative, digest in payload.get("artifact_sha256",{}).items():
        path=config.ROOT/relative
        if not path.exists() or file_digest(path)!=digest:
            raise ValueError(f"Missing/modified result artifact: {relative}; rebuild the producing stage")
    return payload


DEPENDENCIES={
 'clusters':['airport_clusters.csv','airport_archetypes.csv','cluster_k_sweep.csv'],
 'models':['ols_day_clustered_coefficients.csv','quantile90_coefficients.csv','risk_permutation_importance.csv','risk_by_hour.csv','factor_conditional_r2.csv'],
 'attribution':['cause_totals.csv','composition_by_month.csv','carrier_table.csv','cause_quality_exclusions.csv'],
 'tail':['lorenz_curve.csv','percentile_profile.csv','cascade_by_hour.csv','cascade_by_airport.csv'],
 'rotation_pressure':['turnaround_pressure_by_aircraft.csv','cascade_by_hour.csv','cascade_by_airport.csv'],
 'temporal_validation':['temporal_validation.csv'],
 'validation':['source_quality_by_year.csv'],
 'supplementary':['monthly_profile.csv','distance_bands.csv','tail_extreme_sensitivity.csv','carrier_common_support.csv'],
}

def artifact_fingerprints(name):
    return {str(path.relative_to(config.ROOT)).replace('\\','/'):file_digest(path)
            for filename in DEPENDENCIES.get(name,[])
            for path in [config.TABLE_DIR/filename] if path.exists()}
