"""Exact binned summaries and explicitly descriptive sensitivity checks."""
from collections import defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from . import config,models,viz,features,cluster,schema


def histogram_quantile(hist,q):
    h=hist.sort_index();c=h.to_numpy(dtype='int64');v=h.index.to_numpy(dtype=float)
    n=int(c.sum())
    if not n:return float('nan')
    rank=(n-1)*q;lo=int(np.floor(rank));hi=int(np.ceil(rank));cum=np.cumsum(c)
    left=v[np.searchsorted(cum,lo,side='right')];right=v[np.searchsorted(cum,hi,side='right')]
    return float(left+(right-left)*(rank-lo))


def summarize(hist):
    hist=hist.sort_index();n=int(hist.sum());v=hist.index.to_numpy(dtype=float);c=hist.to_numpy(dtype=float)
    return {'flights':n,'mean':float(v@c/n),'median':histogram_quantile(hist,.5),
            'p90':histogram_quantile(hist,.9),'p99':histogram_quantile(hist,.99),
            'share_delayed_60':float(c[v>=60].sum()/n)}


def rebuild_supplementary():
    month=defaultdict(list);bands=defaultdict(list);years=defaultdict(list);cancelled=[];coverage=[]
    for i,batch in enumerate(pq.ParquetFile(config.flights_file()).iter_batches(batch_size=500000,columns=['arr_delay','month','year','distance','cancelled','diverted',*schema.CAUSE_COLUMNS])):
        f=batch.to_pandas()
        cancelled.append(f.assign(n=f.cancelled.eq(1).astype(int)).groupby('year',observed=True).n.sum())
        f=f.loc[f.cancelled.eq(0)&f.diverted.eq(0)&np.isfinite(f.arr_delay)]
        for key,g in f.groupby('month',observed=True):month[int(key)].append(g.arr_delay.value_counts())
        for key,g in f.groupby('year',observed=True):
            years[int(key)].append(g.arr_delay.value_counts())
            above=g.arr_delay.ge(15);known=g[schema.CAUSE_COLUMNS].notna().all(axis=1)
            coverage.append({'year':int(key),'completed':len(g),'above_threshold':int(above.sum()),'known_above':int((known&above).sum()),'known_below':int((known&~above).sum())})
        f=f.assign(band=features.distance_band(f))
        for key,g in f.groupby('band',observed=True):bands[str(key)].append(g.arr_delay.value_counts())
        if i%40==0:print(f'Binned summaries: batch {i}',flush=True)
    mh={key:pd.concat(parts,axis=1).fillna(0).sum(axis=1).astype('int64') for key,parts in month.items()}
    monthly=pd.DataFrame([{'month':key,**summarize(h)} for key,h in sorted(mh.items())]);monthly['month_label']=monthly.month.map(dict(enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)))
    monthly.to_csv(config.TABLE_DIR/'monthly_profile.csv',index=False)
    cancelled_counts=pd.concat(cancelled,axis=1).fillna(0).sum(axis=1)
    annual=[]
    for year,parts in sorted(years.items()):
        h=pd.concat(parts,axis=1).fillna(0).sum(axis=1).astype('int64');v=summarize(h)
        annual.append({'year':year,'completed_flights':v['flights'],'mean_arr_delay':v['mean'],'median_arr_delay':v['median'],'share_delayed_15':float(h.loc[h.index>=15].sum()/h.sum()),'share_delayed_60':v['share_delayed_60'],'cancelled_flights':int(cancelled_counts.loc[year])})
    pd.DataFrame(annual).to_csv(config.TABLE_DIR/'panel_summary_by_year.csv',index=False)
    cv=pd.DataFrame(coverage).groupby('year').sum();cv['coverage_above']=cv.known_above/cv.above_threshold;cv['coverage_below']=cv.known_below/(cv.completed-cv.above_threshold)
    cv[['completed','above_threshold','coverage_above','coverage_below']].to_csv(config.TABLE_DIR/'cause_field_coverage.csv')
    distance=pd.DataFrame([{'band':key,**summarize(pd.concat(bands[key],axis=1).fillna(0).sum(axis=1).astype('int64'))} for key in ['<500','500-900','900-1400','1400-2000','>2000'] if key in bands])
    distance.to_csv(config.TABLE_DIR/'distance_bands.csv',index=False)
    global_hist=pd.concat(mh.values(),axis=1).fillna(0).sum(axis=1).astype('int64');cap=histogram_quantile(global_hist,.999)
    original=summarize(global_hist);trimmed=summarize(global_hist.loc[global_hist.index<=cap])
    winsor=global_hist.rename(index=lambda v:min(v,cap)).groupby(level=0).sum()
    sensitivity=pd.DataFrame([{'specification':'all observed completed','upper_cap':None,**original},
        {'specification':'exclude above full-panel p99.9','upper_cap':cap,**trimmed},
        {'specification':'winsorize above full-panel p99.9','upper_cap':cap,**summarize(winsor)}])
    sensitivity.to_csv(config.TABLE_DIR/'tail_extreme_sensitivity.csv',index=False)
    viz.fig_percentile_band(monthly);viz.fig_mean_bar_vs_band(monthly);viz.fig_distance_bands(distance)
    pearson=float(monthly['mean'].corr(monthly.share_delayed_60));spearman=float(monthly['mean'].corr(monthly.share_delayed_60,method='spearman'))
    # Common-support comparison on the independently validated dashboard sample.
    import sys
    sys.path.insert(0,str(config.ROOT/'dashboard'))
    import data_access
    sample=data_access.load_frame();sample=sample.loc[sample.year.eq(2024)].copy()
    sample['period']=(sample.dep_hour//6).astype(int)
    subset=sample.loc[sample.carrier.isin(['AA','DL'])].copy();subset['severe']=subset.arr_delay.ge(60).astype(int)
    cells=subset.groupby(['origin','period','carrier'],observed=True).agg(n=('severe','size'),events=('severe','sum')).reset_index()
    n=cells.pivot(index=['origin','period'],columns='carrier',values='n').reindex(columns=['AA','DL']);events=cells.pivot(index=['origin','period'],columns='carrier',values='events').reindex(columns=['AA','DL'])
    common=n.ge(30).all(axis=1)
    if common.any():
        n=n.loc[common];events=events.loc[common];weights=n.sum(axis=1)/n.to_numpy().sum()
        standard=(events/n).mul(weights,axis=0).sum();coverage=n.sum()/subset.groupby('carrier',observed=True).size()
        comparison=pd.DataFrame({'standardised_risk':standard,'supported_flights':n.sum(),'sample_retained_fraction':coverage})
        comparison.to_csv(config.TABLE_DIR/'carrier_common_support.csv',index_label='carrier')
    else:comparison=pd.DataFrame()
    models.save_metrics({'mode':config.mode(),'mean_vs_tail':{'pearson_r':pearson,'spearman_r':spearman,
                        'scope':'Twelve pooled calendar-month aggregates; not individual-flight correlation'},
        'extreme_sensitivity':sensitivity,'common_support_carriers':comparison.reset_index(),
        'standardisation_protocol':'2024 dashboard sample, AA vs DL, common origin and six-hour departure blocks, at least 30 completed flights per carrier/cell, pooled common weights; descriptive association, not causal effect',
        'extreme_protocol':'Full observed distribution retained as primary; p99.9 exclusion/winsorization are sensitivity checks, not automatic outlier deletion'},'supplementary')
    return monthly
