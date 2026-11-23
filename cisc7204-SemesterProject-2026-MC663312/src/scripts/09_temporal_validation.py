"""Expanding-window evaluation on a fixed uniform completed-flight sample.

Training ends before each test calendar year. No year fixed effects are used:
an unseen future year cannot have a learned category coefficient. This is a
separate robustness specification, not a rerun of the primary July 2024 holdout.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from team01 import config, models


def split_year(frame, year):
    date = pd.to_datetime(frame['flight_date'])
    return frame.loc[date < pd.Timestamp(year,1,1)], frame.loc[date.ge(pd.Timestamp(year,1,1)) & date.lt(pd.Timestamp(year+1,1,1))]


def paired_week_interval(frame, target, probabilities, baseline_rate, seed=42):
    """Paired weekly-block bootstrap CI of baseline Brier minus model Brier."""
    error = (target-baseline_rate)**2-(target-probabilities)**2
    daily = pd.DataFrame({'date':pd.to_datetime(frame.flight_date).to_numpy(), 'gain':error, 'n':1})
    daily['week']=daily['date'].dt.to_period('W-SUN')
    weekly=daily.groupby('week').agg(gain=('gain','sum'),n=('n','sum'))
    rng=np.random.default_rng(seed)
    pick=rng.integers(0,len(weekly),size=(1000,len(weekly)))
    gains=weekly.gain.to_numpy()[pick].sum(axis=1)/weekly.n.to_numpy()[pick].sum(axis=1)
    return {'brier_gain':float(error.mean()),'gain_ci_low':float(np.quantile(gains,.025)),
            'gain_ci_high':float(np.quantile(gains,.975)),'weekly_blocks':len(weekly)}


def evaluate(frame, years):
    rows=[]
    for year in years:
        train,test=split_year(frame,year)
        if train.empty or test.empty:
            raise ValueError(f'Empty temporal fold: {year}')
        assert pd.to_datetime(train.flight_date).max() < pd.to_datetime(test.flight_date).min()
        x=models.design_matrix(train,controls=[])
        xt=models.design_matrix(test,reference=x,controls=[])
        y=(train.arr_delay>=60).to_numpy(dtype='int8')
        yt=(test.arr_delay>=60).to_numpy(dtype='int8')
        rate=float(y.mean())
        scaler=StandardScaler()
        logit=LogisticRegression(max_iter=2000)
        logit.fit(scaler.fit_transform(x),y)
        tree=HistGradientBoostingClassifier(max_iter=int(config.get("models.gbm_estimators",300)),learning_rate=float(config.get("models.gbm_learning_rate",.05)),max_depth=int(config.get("models.gbm_max_depth",6)),
            early_stopping=True,validation_fraction=.15,random_state=config.seed())
        tree.fit(x,y)
        predictions={'constant_train_rate':np.full(len(test),rate),
            'logistic':logit.predict_proba(scaler.transform(xt))[:,1],
            'gradient_boosting':tree.predict_proba(xt)[:,1]}
        for name,probability in predictions.items():
            row={'test_year':year,'model':name,'train_rows':len(train),'test_rows':len(test),
                'train_end':str(pd.to_datetime(train.flight_date).max().date()),
                'test_start':str(pd.to_datetime(test.flight_date).min().date()),
                **models._classification_metrics(yt,probability,rate),
                **paired_week_interval(test,yt,probability,rate,config.seed())}
            rows.append(row)
        print(f'Completed temporal fold {year}: train={len(train):,}, test={len(test):,}',flush=True)
    return pd.DataFrame(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years',type=int,nargs='+',default=[2019,2020,2022,2024])
    args=parser.parse_args()
    path=config.flights_file().parent/'dashboard_sample.parquet'
    sys.path.insert(0,str(config.ROOT/'dashboard'))
    import data_access
    frame=data_access.load_frame()
    with threadpool_limits(limits=1):
        result=evaluate(frame,args.years)
    result.to_csv(config.TABLE_DIR/'temporal_validation.csv',index=False)
    models.save_metrics({'mode':config.mode(),'sample_rows':len(frame),'seed':config.seed(),
        'protocol':'Expanding training window; whole test calendar year; training-only preprocessing; no year/COVID controls; fixed model parameters; no tuning on folds',
        'sample_scope':'Existing fixed uniform completed-flight sample; distinct from the primary half-year specification',
        'uncertainty':'Paired resampling of calendar-week blocks within each test year, 1000 draws; conditional on the fixed sample and fitted models',
        'results':result},'temporal_validation')
    # The figure lives in team01.viz with the rest of them: an inline copy could
    # not pick up the shared style, the provenance stamp or the fixes that the
    # rest of the figure library received, and this was the only chart in the
    # report whose axis conventions differed from every other one.
    from team01 import viz
    viz.fig_temporal_validation(result, args.years)
    print(result[['test_year','model','roc_auc','brier','brier_gain']].to_string(index=False))

if __name__=='__main__':main()
