"""Regression coverage for the November correctness audit, including counterexamples."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from team01 import config,models,clean,attribution,rotation_pressure,cluster,provenance,schema


def test_inference_design_has_no_dummy_trap(completed):
    matrix=models.design_matrix(completed)
    assert np.linalg.matrix_rank(matrix)==matrix.shape[1]
    levels=matrix.attrs['factor_levels']['dep_hour']
    assert f'dep_hour_{levels[0]}' not in matrix


def test_full_mode_rejects_invalid_holdout(completed,monkeypatch):
    monkeypatch.setattr(config,'mode',lambda:'full')
    with pytest.raises(ValueError,match='Holdout boundary'):
        models.time_split(completed,holdout_start='2030-01-01')


def test_demo_split_never_shares_dates(monkeypatch):
    monkeypatch.setattr(config,'mode',lambda:'sample')
    frame=pd.DataFrame({'flight_date':pd.to_datetime(['2025-01-01']*9+['2025-01-02']*3)})
    a,b=models.time_split(frame,'2030-01-01')
    assert a.flight_date.max()<b.flight_date.min()
    with pytest.raises(ValueError,match='two distinct'):
        models.time_split(frame.iloc[:2],'2030-01-01')


def test_completed_is_not_a_mutable_attr_cache():
    frame=pd.DataFrame({'cancelled':[0.,np.nan],'diverted':[0.,0.],'arr_delay':[0.,0.]})
    result=clean.completed(frame)
    assert len(result)==1
    result.loc[:,'cancelled']=1
    assert clean.completed(result).empty


def test_missing_hhmm_is_audited_not_integer_cast_error():
    frame=pd.DataFrame({'flight_date':pd.to_datetime(['2024-01-01']*2),'crs_dep_time':[np.nan,2400.],
        'origin':['ATL']*2,'crs_elapsed':[60.]*2,'arr_delay':[0.]*2})
    result=rotation_pressure.add_utc_times(frame,{'ATL':'America/New_York'})
    assert result.loc[0,'utc_status']=='invalid_clock'
    assert pd.isna(result.loc[0,'dep_hour']) and pd.isna(result.loc[0,'sched_dep_utc'])
    assert result.loc[1,'sched_dep_utc']==pd.Timestamp('2024-01-02 05:00',tz='UTC')


def test_partial_causes_use_one_population_for_point_and_interval():
    f=pd.DataFrame({'flight_date':pd.to_datetime(['2024-01-01','2024-01-02']),
        'arr_delay':[20.,20.],'min_carrier':[10.,10.],'min_late_aircraft':[0.,np.nan],
        'min_nas':[10.,10.],'min_weather':[0.,0.],'min_security':[0.,0.]})
    known,audit=attribution.cause_population(f)
    assert len(known)==1 and audit['incomplete_or_invalid']==1
    assert attribution.family_split(f)['internal_share']==attribution.bootstrap_family_share(f,reps=20)['share']==.5


def test_low_count_carriers_remain_hidden():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
    import data_access
    assert data_access.carrier_profile(pd.DataFrame({'carrier':['AA'],'arr_delay':[100.]})).empty


def test_block_shuffle_preserves_onehot_rows(monkeypatch):
    class Estimator:
        def predict_proba(self,x):
            assert x[['dep_hour_0','dep_hour_1']].sum(axis=1).eq(1).all()
            p=.1+.8*x.dep_hour_1.to_numpy()
            return np.stack([1-p,p],axis=1)
    x=pd.DataFrame({'const':1.,'dep_hour_0':[1,0]*20,'dep_hour_1':[0,1]*20})
    result=models.block_importance(Estimator(),x,x.dep_hour_1.to_numpy(),repeats=3)
    assert result.factor.tolist()==['dep_hour'] and result.importance.iloc[0]>0


def test_sample_paths_are_isolated(monkeypatch):
    monkeypatch.setattr(config,'mode',lambda:'sample')
    assert 'sample' in config.path('paths.metrics').parts
    assert 'sample' in config.airports_clustered_file().parts
    monkeypatch.setattr(config,'mode',lambda:'full')
    assert config.path('paths.metrics')==config.ROOT/'outputs/metrics'


def test_provenance_rejects_stale_source(monkeypatch):
    monkeypatch.setattr(provenance,'signature',lambda:{'mode':'full','source_sha256':'current'})
    with pytest.raises(ValueError,match='Stale'):
        provenance.check({'run_signature':{'mode':'full','source_sha256':'old'}})


def test_provenance_rejects_modified_result(tmp_path,monkeypatch):
    path=tmp_path/'table.csv';path.write_text('old',encoding='utf-8')
    digest=provenance.file_digest(path)
    monkeypatch.setattr(config,'ROOT',tmp_path)
    monkeypatch.setattr(provenance,'signature',lambda:{'source':'same'})
    path.write_text('changed',encoding='utf-8')
    with pytest.raises(ValueError,match='modified result'):
        provenance.check({'run_signature':{'source':'same'},'artifact_sha256':{'table.csv':digest}})


def test_k_stability_identifies_its_reference(completed,airport_reference):
    from team01 import features
    matrix=features.airport_feature_matrix(completed,airport_reference,min_departures=1)
    score=cluster.stability(matrix,3,draws=2)
    assert 'configured full fit reference' in score['protocol']


def test_source_merge_ignores_old_years(tmp_path,monkeypatch):
    """Run acquisition main with fake downloads and real parquet staging/merge."""
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('acquire_audit',root/'src/scripts/01_acquire.py')
    entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
    staging=tmp_path/'interim/flights_year';staging.mkdir(parents=True)
    pd.DataFrame({'year':[2015]}).to_parquet(staging/'flights_2015.parquet',index=False)
    ref=tmp_path/'airports.csv';ref.write_text('fixture',encoding='utf-8')
    raw=pd.DataFrame({'year':[2024],'flight_date':pd.to_datetime(['2024-01-01']),'origin':['ATL'],'crs_dep_time':[800]})
    monkeypatch.setattr(entry.config,'INTERIM_DIR',tmp_path/'interim')
    monkeypatch.setattr(entry.config,'TABLE_DIR',tmp_path/'tables')
    monkeypatch.setattr(entry.config,'flights_file',lambda:tmp_path/'flights.parquet')
    monkeypatch.setattr(entry.io,'acquire_airports',lambda **kw:ref)
    monkeypatch.setattr(entry.io,'acquire_month',lambda *a,**kw:ref)
    monkeypatch.setattr(entry.io,'read_bts_month',lambda p:raw)
    monkeypatch.setattr(entry.io,'write_manifest',lambda p:None)
    monkeypatch.setattr(entry.clean,'apply_schema',lambda p:p)
    monkeypatch.setattr(entry.clean,'drop_duplicates',lambda p:p)
    monkeypatch.setattr(entry.clean,'validate',lambda f,stage:{'rows':len(f)})
    import sys
    monkeypatch.setattr(sys,'argv',['01_acquire.py','--years','2024','--limit-months','1'])
    assert entry.main()==0
    assert pd.read_parquet(tmp_path/'flights.parquet').year.tolist()==[2024]


def test_weighted_histogram_matches_numpy_quantiles():
    from team01.supplementary import histogram_quantile
    values=np.array([-238.,-6.,-6.,0.,15.,60.,4405.])
    hist=pd.Series(values).value_counts()
    for q in [0,.01,.5,.9,.999,1]:
        assert histogram_quantile(hist,q)==pytest.approx(np.quantile(values,q))


def test_reference_pin_mismatch_is_not_silently_accepted(tmp_path,monkeypatch):
    import json
    source=tmp_path/'source';source.write_text('data',encoding='utf-8')
    ref=tmp_path/'ref.csv';ref.write_text('modified',encoding='utf-8')
    (tmp_path/'config').mkdir()
    (tmp_path/'config/reference_snapshots.json').write_text(json.dumps({'references':[{'path':'ref.csv','sha256':'previous'}]}),encoding='utf-8')
    monkeypatch.setattr(config,'ROOT',tmp_path)
    monkeypatch.setattr(config,'mode',lambda:'full')
    monkeypatch.setattr(config,'flights_file',lambda:source)
    with pytest.raises(ValueError,match='Reference snapshot mismatch'):
        provenance.signature()


def test_airport_missing_cause_mix_is_not_median_imputed(airport_reference):
    from team01 import features
    frame=pd.DataFrame({'origin':['ATL']*3,'month':[1]*3,'arr_delay':[0.,0.,0.],
                        **{c:[np.nan]*3 for c in schema.CAUSE_COLUMNS}})
    with pytest.raises(ValueError,match='Unavailable airport analytical features'):
        features.airport_feature_matrix(frame,airport_reference,min_departures=1)


def test_map_volume_profile_respects_cap_and_true_counts(completed):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
    import data_access
    profile=data_access.airport_profile(completed,top_n=2)
    expected=completed.origin.astype(str).value_counts().iloc[:2]
    assert set(profile.origin.astype(str))==set(expected.index)
    assert profile.set_index('origin').flights.to_dict()==expected.to_dict()
