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
    audit = config.TABLE_DIR / 'airport_metadata_audit.csv'
    table = pd.read_csv(audit if audit.exists() else config.airports_clustered_file())
    if not table['origin'].is_unique:
        raise ValueError('Existing airport aggregates are not one row per airport')
    numeric = table[['origin', *[c for c in schema.AIRPORT_FEATURES if c != 'hub_stratum']]]
    matrix = airports.attach_metadata(numeric.set_index('origin'), io.load_airports()).reset_index()
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
                         'aggregate_provenance': 'Unchanged flight aggregates from existing full-panel airport_clusters.csv; metadata and clusters recomputed',
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
        good = frame.loc[frame.cancelled.eq(0) & frame.diverted.eq(0) & frame.arr_delay.notna()]
        lo, hi = np.searchsorted(indices, [offset, offset+len(good)])
        if hi > lo:
            parts.append(good.iloc[indices[lo:hi]-offset])
        offset += len(good)
    if offset != total:
        raise ValueError(f'Source completed count changed: {offset} != {total}')
    return features.add_panel_controls(pd.concat(parts, ignore_index=True))


def rebuild_models():
    print('Selecting uniform model sample from full panel...', flush=True)
    sample = model_sample()
    print(f'Fitting risk models on {len(sample):,} flights...', flush=True)
    risk = models.risk_classifier(sample)
    old = models.load_metrics('models')
    old['risk'] = risk
    old['risk_rebuild_note'] = 'Uniform 400000 completed-flight sample; training-only category mapping; unweighted logistic; held-out calibration and constant-training-rate baseline'
    models.save_metrics(old, 'models')
    risk['hour_response'].to_csv(config.TABLE_DIR/'risk_by_hour.csv', index=False)
    pd.DataFrame(risk['models']['importance']).to_csv(config.TABLE_DIR/'risk_permutation_importance.csv',index=False)
    models.save_metrics({'mode':config.mode(), 'risk':risk}, 'risk_evaluation')
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
    viz.fig_cascade_hour(result['hourly'])
    print('ROTATION PRESSURE:', {k:result[k] for k in ['sample_rows','rotations','aircraft_sampled','missing_utc_rows','pressure_to_positive_arrival_ratio']},flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=['all','airports','models','rotations'],default='all')
    parser.add_argument('--tails',type=int,default=256)
    args=parser.parse_args()
    for name, func in [('airports',rebuild_airports),('models',rebuild_models),('rotations',lambda:rebuild_rotations(args.tails))]:
        if args.part in ('all',name):
            func()
if __name__=='__main__':
    main()
