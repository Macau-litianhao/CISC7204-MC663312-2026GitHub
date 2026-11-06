"""Regression cases for the real defects found during the project review."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from team01 import airports, models, features, synth, clean
from team01.rotation_pressure import add_utc_times


def test_icao_ident_does_not_break_iata_join():
    reference=pd.DataFrame({'ident':['KATL'],'iata_code':['ATL'],'local_code':['ATL'],
        'latitude_deg':[33.64],'longitude_deg':[-84.43],'type':['large_airport'],
        'name':['Atlanta'],'municipality':['Atlanta']})
    result=airports.attach_metadata(pd.DataFrame({'n_dep':[100]},index=['ATL']),reference)
    assert result.loc['ATL','latitude_deg'] == pytest.approx(33.64)
    assert result.loc['ATL','metadata_matched']


def test_duplicate_mapping_is_rejected():
    frame=pd.DataFrame({'ident':['KATL','ZZZZ'],'iata_code':['ATL','ATL']})
    with pytest.raises(ValueError,match='Ambiguous'):
        airports.reference_by_code(frame)


def test_all_unmatched_airports_fail():
    reference=synth.make_airport_reference()
    with pytest.raises(ValueError,match='No airports matched'):
        airports.attach_metadata(pd.DataFrame({'n_dep':[10]},index=['ZZZ']),reference)


def test_training_year_dummy_survives_single_year_holdout():
    train=pd.DataFrame({'year':[2022,2023,2024],'origin':['ATL','DFW','ATL']})
    test=pd.DataFrame({'year':[2024],'origin':['DFW']})
    x=models.design_matrix(train,factors=['origin'],controls=['year'])
    y=models.design_matrix(test,factors=['origin'],controls=['year'],reference=x)
    assert y.loc[0,'year_2024'] == 1
    assert y.loc[0,'origin_DFW'] == 1


def test_design_matrix_retains_noncontiguous_source_index():
    frame=pd.DataFrame({'year':[2022,2023,2024],'origin':['ATL','DFW','ATL']},index=[5,8,20])
    matrix=models.design_matrix(frame,factors=['origin'],controls=['year'])
    assert matrix.index.equals(frame.index)
    assert np.isfinite(matrix.to_numpy()).all()


def test_streamed_sampling_checks_counts_and_excludes_cancelled(tmp_path,monkeypatch):
    from team01 import io,config
    frame=pd.DataFrame({'record':range(6),'cancelled':[0,1,0,0,0,0],
        'diverted':[0,0,0,1,0,0],'arr_delay':[0.,np.nan,10.,np.nan,30.,60.]})
    source=tmp_path/'flights.parquet'
    frame.to_parquet(source,index=False)
    (tmp_path/'validation.json').write_text(json.dumps({'completed_flights':4}))
    monkeypatch.setattr(config,'flights_file',lambda:source)
    monkeypatch.setattr(config,'mode',lambda:'full')
    monkeypatch.setattr(config,'METRIC_DIR',tmp_path)
    from team01 import provenance
    (tmp_path/'validation.json').write_text(json.dumps({'completed_flights':4,'run_signature':provenance.signature()}))
    result=io.sample_completed(frame.columns.tolist(),limit=3)
    assert len(result)==3 and set(result.record)<= {0,2,4,5}
    (tmp_path/'validation.json').write_text(json.dumps({'completed_flights':5,'run_signature':provenance.signature()}))
    with pytest.raises(ValueError,match='Validation count stale'):
        io.sample_completed(frame.columns.tolist(),limit=3)


def test_metrics_are_strict_json_records():
    result=models.json_safe({'table':pd.DataFrame({'x':[1.,np.nan]}),'bad':float('inf')})
    assert result['table'] == [{'x':1.},{'x':None}]
    assert json.loads(json.dumps(result,allow_nan=False))['bad'] is None


def test_utc_and_2400_cross_day():
    source=pd.DataFrame({'flight_date':pd.to_datetime(['2024-01-01','2024-01-01']),
        'crs_dep_time':[2400,800],'origin':['ATL','LAX'],'crs_elapsed':[120,120],'arr_delay':[0,0]})
    result=add_utc_times(source,{'ATL':'America/New_York','LAX':'America/Los_Angeles'})
    assert result.loc[0,'sched_dep_utc'] == pd.Timestamp('2024-01-02 05:00',tz='UTC')
    assert result.loc[1,'sched_dep_utc'] == pd.Timestamp('2024-01-01 16:00',tz='UTC')


def test_ambiguous_dst_times_are_not_guessed():
    source=pd.DataFrame({'flight_date':pd.to_datetime(['2024-11-03','2024-03-10']),
        'crs_dep_time':[130,230],'origin':['ATL','ATL'],'crs_elapsed':[120,120],'arr_delay':[0,0]})
    assert add_utc_times(source,{'ATL':'America/New_York'})['sched_dep_utc'].isna().all()


def dashboard_modules():
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'dashboard'))
    import callbacks
    return callbacks


def test_airport_is_preserved_in_shared_state():
    callbacks=dashboard_modules()
    url=callbacks._build_search(2024,['AA'],[6,8],airport='ATL')
    assert callbacks._airport_from_search(url) == 'ATL'
    assert callbacks._parse_search(url) == (2024,['AA'],[6,8])
    assert callbacks._parse_search('?months=99-0')[2] == [1,12]
    assert callbacks._airport_from_search('?airport=<script>') is None


def test_overflow_histogram_preserves_counts():
    dashboard_modules()
    from panels.dist import distribution_figure
    fig=distribution_figure(pd.DataFrame({'arr_delay':[-100,-60,0,240,900]}))
    assert sum(fig.data[0].y) == 5
    assert fig.data[0].y[0] == 1
    assert fig.data[0].y[-1] == 2


def test_bubble_area_is_proportional_to_volume():
    dashboard_modules()
    from panels.geo import _bubble_sizes
    diameter=_bubble_sizes([100,400],400)
    assert (diameter[1]/diameter[0])**2 == pytest.approx(4)


def test_monthly_composition_is_stacked_bars(completed):
    dashboard_modules()
    from panels.monthly import monthly_figure
    fig=monthly_figure(completed)
    assert all(trace.type=='bar' for trace in fig.data)
    assert fig.layout.barmode=='stack'


def test_reader_text_does_not_claim_airline_control(completed):
    dashboard_modules()
    import narrative, captions
    text=' '.join(str(x) for x in narrative.insights(completed))+captions.cause(completed)
    assert 'causes the airline controls' not in text
    assert 'does not establish' in text or 'not a measure' in text
