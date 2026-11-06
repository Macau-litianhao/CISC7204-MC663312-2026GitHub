"""Rebuild reviewed outputs without materialising the entire panel in memory.

python src/scripts/08_review_rebuild.py --part airports|models|rotations|all
Airport numerical aggregates are reused only after their schema/row uniqueness
is checked; metadata, clustering and figures are recomputed. Model samples are
uniform samples of completed flights selected across the complete source file.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from team01 import airports, cluster, config, features, io, models, rotation_pressure, schema, viz


def rebuild_airports():
    from team01.stream_rebuild import rebuild_source
    matrix = rebuild_source()
    missing = matrix.loc[~matrix['metadata_matched'], 'origin'].tolist()
    matrix.to_csv(config.TABLE_DIR / 'airport_metadata_audit.csv', index=False)
    # Explicit complete-case selection, never a neutral metadata replacement.
    included = matrix.loc[matrix['metadata_matched'] & matrix['hub_stratum'].notna()].copy()
    included.to_parquet(config.airport_features_file(), index=False)
    sweep = cluster.sweep_k(included)
    k = cluster.choose_k(sweep)
    labelled, _, _ = cluster.fit(included, k)
    names = cluster.name_clusters(labelled)
    labelled['archetype'] = labelled['cluster'].map(names)
    cluster.save(labelled)
    profiles = cluster.cluster_table(labelled)
    sweep.to_csv(config.TABLE_DIR/'cluster_k_sweep.csv', index=False)
    profiles.to_csv(config.TABLE_DIR/'airport_archetypes.csv', index=False)
    stability = cluster.stability(included, k)
    models.save_metrics({'mode': config.mode(), 'chosen_k': int(k), 'airports': len(included),
                         'input_airports': len(matrix), 'unmatched_airports': missing,
                         'metadata_match_rate': float(matrix['metadata_matched'].mean()),
                         'airport_type_note': 'Physical airport type proxy; not FAA hub classification',
                         'aggregate_provenance': 'Fresh full-source streamed aggregates, reconciled cause population and content fingerprints',
                         'features': schema.AIRPORT_FEATURES, 'sweep': sweep,
                         'stability': stability, 'archetypes': profiles,
                         'ward': {'cophenetic_correlation': cluster.ward_check(included)['cophenetic_correlation']}}, 'clusters')
    row = sweep.loc[sweep.k.eq(k)].iloc[0]
    viz.fig_silhouette(sweep, k)
    viz.fig_cluster_scatter(labelled, names, stats={'k':k,'silhouette':float(row.silhouette),
        'ari':stability['mean_ari'],'airports':len(included),'pc_variance':cluster.pc_variance(included)})
    print(f'AIRPORTS: {len(included)}/{len(matrix)} valid, missing={missing}', flush=True)


def model_sample(rows=400_000):
    validation = models.load_metrics('validation')
    total = int(validation['completed_flights'])
    indices = np.sort(np.random.default_rng(config.seed()).choice(total, min(rows,total), replace=False))
    columns = ['year','month','flight_date','carrier','origin','distance','arr_delay','cancelled','diverted','dep_hour']
    offset = 0
    parts = []
    for batch in pq.ParquetFile(config.flights_file()).iter_batches(batch_size=500_000, columns=columns):
        frame = batch.to_pandas()
        good = frame.loc[frame.cancelled.eq(0) & frame.diverted.eq(0) & np.isfinite(frame.arr_delay)]
        lo, hi = np.searchsorted(indices, [offset, offset+len(good)])
        if hi > lo:
            parts.append(good.iloc[indices[lo:hi]-offset])
        offset += len(good)
    if offset != total:
        raise ValueError(f'Source completed count changed: {offset} != {total}')
    return features.add_panel_controls(pd.concat(parts, ignore_index=True))


def rebuild_models():
    print('Selecting uniform inference sample from full panel...', flush=True)
    sample = model_sample(rows=int(config.get('sampling.ols_rows',600000)))
    ranking = models.incremental_r2(sample)
    conditional = models.conditional_factor_r2(sample)
    print('Fitting day-clustered OLS...',flush=True)
    ols = models.ols_with_robust_errors(sample)
    print('Fitting signed-delay p90 quantile regression...',flush=True)
    quantile = models.quantile_regression(sample)
    print('Fitting risk models and joint-block importance...',flush=True)
    risk = models.risk_classifier(sample)
    sensitivity = models.sensitivity_exclude_years(sample)
    ranking.to_csv(config.TABLE_DIR/'factor_incremental_r2.csv',index=False)
    conditional.to_csv(config.TABLE_DIR/'factor_conditional_r2.csv',index=False)
    ols['table'].to_csv(config.TABLE_DIR/'ols_day_clustered_coefficients.csv',index=False)
    quantile['table'].to_csv(config.TABLE_DIR/'quantile90_coefficients.csv',index=False)
    risk['hour_response'].to_csv(config.TABLE_DIR/'risk_by_hour.csv',index=False)
    pd.DataFrame(risk['models']['importance']).to_csv(config.TABLE_DIR/'risk_permutation_importance.csv',index=False)
    pd.json_normalize([{'set':'with_all_years',**sensitivity['with_excluded']},{'set':'excluding_selected_years',**sensitivity['without_excluded']}]).to_csv(config.TABLE_DIR/'sensitivity_excluded_years.csv',index=False)
    models.save_metrics({'mode':config.mode(),'controls':models.active_controls(sample),
        'ranking':ranking,'conditional_r2':conditional,'model_r2':ranking.attrs['model_r2'],
        'ols':{k:v for k,v in ols.items() if k!='table'},
        'quantile90':{k:v for k,v in quantile.items() if k!='table'},
        'risk':risk,'sensitivity':sensitivity,
        'risk_rebuild_note':'Uniform inference sample followed by explicit seeded model subsamples; reference coding; operating-day clustered OLS; signed quantile target; joint block importance'},'models')
    models.save_metrics({'mode':config.mode(),'risk':risk},'risk_evaluation')
    viz.fig_importance(pd.DataFrame(risk['models']['importance']))
    viz.fig_hour_response(risk['hour_response'],threshold=60)
    print('MODEL METRICS:', {k:v for k,v in risk['models'].items() if k!='importance'},flush=True)


def rebuild_rotations(tails):
    result = rotation_pressure.analyse_file(config.flights_file(), tails=tails)
    result['hourly'].to_csv(config.TABLE_DIR/'cascade_by_hour.csv',index=False)
    result['by_airport'].to_csv(config.TABLE_DIR/'cascade_by_airport.csv',index=False)
    result['by_aircraft'].to_csv(config.TABLE_DIR/'turnaround_pressure_by_aircraft.csv',index=False)
    old = models.load_metrics('tail')
    old['cascade'] = {k:v for k,v in result.items() if k not in ('hourly','by_airport','by_aircraft')}
    old['cascade_by_hour'] = result['hourly']
    models.save_metrics(old,'tail')
    models.save_metrics(result,'rotation_pressure')
    viz.fig_cascade_hour(result['hourly'],min_turnaround=result['min_turnaround_minutes'])
    print('ROTATION PRESSURE:', {k:result[k] for k in ['sample_rows','rotations','aircraft_sampled','missing_utc_rows','pressure_to_positive_arrival_ratio']},flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=['all','airports','models','rotations'],default='all')
    parser.add_argument('--tails',type=int,default=256)
    args=parser.parse_args()
    # All references must exist before any run fingerprints are emitted.
    rotation_pressure.timezone_reference()
    for name, func in [('airports',rebuild_airports),('models',rebuild_models),('rotations',lambda:rebuild_rotations(args.tails))]:
        if args.part in ('all',name):
            func()
if __name__=='__main__':
    main()
