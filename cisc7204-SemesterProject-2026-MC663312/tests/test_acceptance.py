"""Acceptance regressions: geographic scope and temporal-validation protocol."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('temporal_validation',ROOT/'src/scripts/09_temporal_validation.py')
temporal=importlib.util.module_from_spec(spec)
spec.loader.exec_module(temporal)


def test_temporal_fold_never_trains_on_future_year():
    frame=pd.DataFrame({'flight_date':pd.to_datetime(['2022-12-31','2023-01-01','2023-12-31','2024-01-01'])})
    train,test=temporal.split_year(frame,2023)
    assert len(train)==1 and len(test)==2
    assert train.flight_date.max()<test.flight_date.min()


def test_paired_week_bootstrap_keeps_known_error_gain():
    frame=pd.DataFrame({'flight_date':pd.date_range('2024-01-01',periods=28)})
    result=temporal.paired_week_interval(frame,np.zeros(28),np.zeros(28),.2)
    assert result['brier_gain']==pytest.approx(.04)
    assert result['gain_ci_low']==pytest.approx(.04)
    assert result['gain_ci_high']==pytest.approx(.04)


def test_map_scope_does_not_call_territory_a_state():
    sys.path.insert(0,str(ROOT/'dashboard'))
    import data_access
    frame=pd.DataFrame({'origin_state':['CA','PR'],'arr_delay':[10.,200.]})
    profile=data_access.state_profile(frame)
    assert profile.origin_state.tolist()==['CA']
    assert len(frame)==2  # Map scope does not remove territory records from KPIs.
