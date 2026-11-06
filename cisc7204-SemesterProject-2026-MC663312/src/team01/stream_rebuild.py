"""Bounded-memory full-source rebuild; no cached airport aggregates are reused."""
from collections import defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from . import config,schema,attribution,airports,io,models,tail,viz


def rebuild_source():
    columns=['origin','dest','origin_state','carrier','tail_number','flight_date','year','month',
             'crs_dep_time','dep_hour','arr_delay','distance','cancelled','diverted',*schema.CAUSE_COLUMNS]
    delays=defaultdict(list);monthly_parts=[];cause_parts=defaultdict(list);state_parts=[];issues=[]
    counts=defaultdict(int);year_parts=[]
    for i,batch in enumerate(pq.ParquetFile(config.flights_file()).iter_batches(batch_size=500000,columns=columns)):
        frame=batch.to_pandas();counts['rows']+=len(frame)
        flags=frame[['cancelled','diverted']]
        counts['invalid_flags']+=int((~flags.isin([0,1]).all(axis=1)).sum())
        counts['missing_operated_delay']+=int((flags.eq(0).all(axis=1)&frame.arr_delay.isna()).sum())
        if frame.flight_date.isna().any():raise ValueError('Missing dates')
        clock=frame.crs_dep_time
        if not (clock.between(0,2400)&clock.mod(100).lt(60)).all():raise ValueError('Invalid schedule clock')
        good=frame.loc[flags.eq(0).all(axis=1)&np.isfinite(frame.arr_delay)]
        if good[['distance','flight_date','origin','dest','carrier']].isna().any().any() or not np.isfinite(good.distance).all() or good.distance.le(0).any():
            raise ValueError('Invalid completed-flight predictors')
        if frame.year.ne(frame.flight_date.dt.year).any() or frame.month.ne(frame.flight_date.dt.month).any() or frame.dep_hour.ne((clock//100)%24).any():
            raise ValueError('Calendar/clock derived fields disagree with source')
        counts['completed']+=len(good)
        for code,g in good.groupby('origin',observed=True):delays[str(code)].append(g.arr_delay.to_numpy(dtype='float32'))
        good=good.copy();good['arr_delay']=good.arr_delay.astype('float64')
        monthly_parts.append(good.groupby(['origin','month'],observed=True).arr_delay.agg(total='sum',n='size').reset_index())
        # All additive accumulators use float64.
        good=good.copy();good['arr_delay']=good.arr_delay.astype('float64')
        year_parts.append(good.assign(severe=good.arr_delay.ge(60).astype(int)).groupby('year',observed=True).agg(n=('arr_delay','size'),total=('arr_delay','sum'),severe=('severe','sum')).reset_index())
        state_parts.append(good.groupby('origin_state',observed=True).arr_delay.agg(total='sum',n='size').reset_index())
        eligible=good.loc[good.arr_delay.ge(config.threshold())]
        known,audit=attribution.cause_population(good)
        bad=eligible.loc[~eligible.index.isin(known.index)]
        if len(bad):issues.append(bad[['flight_date','carrier','tail_number','origin','dest','arr_delay',*schema.CAUSE_COLUMNS]])
        for key,value in audit.items():counts['cause_'+key]+=value
        if len(known):
            # ~11M delayed rows are reduced to daily/carrier/airport/month sums per batch.
            for key in ['flight_date','year','month','carrier','origin']:
                c=known.assign(flights=1).groupby(key,observed=True)[schema.CAUSE_COLUMNS+['flights']].sum().reset_index()
                cause_parts[key].append(c)
        if i%20==0:print(f'Stream rebuild: {counts["rows"]:,} rows',flush=True)
    if counts['invalid_flags']:raise ValueError('Unknown cancellation/diversion flags')
    values={code:np.concatenate(parts) for code,parts in delays.items()}
    del delays
    matrix=pd.DataFrame([{'origin':code,'n_dep':len(v),'mean_arr_delay':float(v.astype(float).mean()),
                         'p90_arr_delay':float(np.quantile(v,.9)),'share_delayed_60':float((v>=60).mean())}
                         for code,v in values.items()]).set_index('origin')
    monthly=pd.concat(monthly_parts).groupby(['origin','month'],observed=True)[['total','n']].sum()
    amplitude=(monthly.total/monthly.n).unstack('month');matrix['seasonal_amplitude']=amplitude.max(axis=1)-amplitude.min(axis=1)
    cause={key:pd.concat(parts,ignore_index=True).groupby(key,observed=True)[schema.CAUSE_COLUMNS+['flights']].sum() for key,parts in cause_parts.items()}
    del cause_parts
    sums=cause['origin'][schema.CAUSE_COLUMNS];total=sums.sum(axis=1)
    for target,numerator in [('share_internal',sums.min_carrier+sums.min_late_aircraft),('share_late_aircraft',sums.min_late_aircraft),('share_nas',sums.min_nas),('share_weather',sums.min_weather)]:matrix[target]=numerator/total
    matrix=matrix.loc[matrix.n_dep.ge(int(config.get('cluster.min_departures',20000)))]
    matrix=airports.attach_metadata(matrix,io.load_airports()).reset_index()
    if matrix[schema.AIRPORT_FEATURES].isna().any().any():raise ValueError('Incomplete airport features; explicit resolution required')
    matrix.to_csv(config.TABLE_DIR/'airport_metadata_audit.csv',index=False)
    matrix.to_parquet(config.ensure_parent(config.airport_features_file()),index=False)
    pd.concat(issues).to_csv(config.TABLE_DIR/'cause_quality_exclusions.csv',index=False) if issues else None
    yearly=pd.concat(year_parts).groupby('year').sum()
    yearly.assign(mean_arr_delay=yearly.total/yearly.n,share_delayed_60=yearly.severe/yearly.n).reset_index().to_csv(config.TABLE_DIR/'source_quality_by_year.csv',index=False)
    models.save_metrics({'mode':config.mode(),'completed_flights':int(counts['completed']),
                         'years':[int(y) for y in yearly.index],'checks':dict(counts),
                         'share_delayed_60':float(yearly.severe.sum()/yearly.n.sum()),
                         'method':'Fresh streamed source counts; unknown flags rejected; cause eligibility audited'},'validation')
    # Recalculate attribution from the same reconciled reported records.
    grand=cause['origin'][schema.CAUSE_COLUMNS].sum();den=float(grand.sum())
    split={'attributed_minutes':den,'internal_minutes':float(grand.min_carrier+grand.min_late_aircraft),
           'system_minutes':float(grand.min_nas+grand.min_weather+grand.min_security),
           'internal_share':float((grand.min_carrier+grand.min_late_aircraft)/den),
           'system_share':float((grand.min_nas+grand.min_weather+grand.min_security)/den),'late_aircraft_share':float(grand.min_late_aircraft/den)}
    daily=cause['flight_date'][schema.CAUSE_COLUMNS]
    rng=np.random.default_rng(config.seed());internal=(daily.min_carrier+daily.min_late_aircraft).to_numpy();total=daily.sum(axis=1).to_numpy()
    picks=rng.integers(0,len(daily),(400,len(daily)));ratios=internal[picks].sum(axis=1)/total[picks].sum(axis=1)
    bootstrap={'share':split['internal_share'],'ci_low':float(np.quantile(ratios,.025)),'ci_high':float(np.quantile(ratios,.975)),'reps':400,'days':len(daily)}
    stability=[]
    for year,g in cause['year'].iterrows():
        v=g[schema.CAUSE_COLUMNS];d=float(v.sum());stability.append({'year':int(year),'attributed_minutes':d,'internal_share':float((v.min_carrier+v.min_late_aircraft)/d),'system_share':float((v.min_nas+v.min_weather+v.min_security)/d),'late_aircraft_share':float(v.min_late_aircraft/d)})
    totals=grand.rename('minutes').rename_axis('cause_key').reset_index();totals['share']=totals.minutes/den;totals['cause']=totals.cause_key.map(schema.CAUSE_LABELS);totals['family']=totals.cause_key.map(schema.CAUSE_FAMILY);totals=totals.sort_values('minutes',ascending=False)
    totals.to_csv(config.TABLE_DIR/'cause_totals.csv',index=False);pd.DataFrame(stability).to_csv(config.TABLE_DIR/'attribution_stability_by_year.csv',index=False)
    month=cause['month'][schema.CAUSE_COLUMNS];shares=month.div(month.sum(axis=1),axis=0).reset_index().melt('month',var_name='cause_key',value_name='share');shares['cause']=shares.cause_key.map(schema.CAUSE_LABELS);shares['family']=shares.cause_key.map(schema.CAUSE_FAMILY);shares.to_csv(config.TABLE_DIR/'composition_by_month.csv',index=False)
    cs=cause['carrier'].copy();cs['delay_minutes']=cs[schema.CAUSE_COLUMNS].sum(axis=1);cs['internal_share']=(cs.min_carrier+cs.min_late_aircraft)/cs.delay_minutes;cs['late_aircraft_share']=cs.min_late_aircraft/cs.delay_minutes;cs['minutes_per_flight']=cs.delay_minutes/cs.flights
    carriers=cs.loc[cs.flights.ge(int(config.get_for_mode('attribution.carrier_min_flights',5000))),['flights','delay_minutes','internal_share','late_aircraft_share','minutes_per_flight']].sort_values('minutes_per_flight',ascending=False).reset_index();carriers.to_csv(config.TABLE_DIR/'carrier_table.csv',index=False)
    state=pd.concat(state_parts).groupby('origin_state',observed=True)[['total','n']].sum();state=(state.total/state.n).round(2);state.to_csv(config.TABLE_DIR/'mean_delay_by_state.csv',header=['mean_arr_delay'])
    viz.fig_cause_waffle(totals);viz.fig_monthly_composition(shares);viz.fig_carrier_bars(carriers);viz.fig_state_tile(state,metric_label='Mean arrival delay (min)')
    models.save_metrics({'mode':config.mode(),'split':split,'bootstrap':bootstrap,'stability':stability,
                        'attribution_universe':int(counts['cause_retained']),'completed_flights':counts['completed'],
                        'quality_exclusions':{k:v for k,v in counts.items() if k.startswith('cause_')}},'attribution')
    # Recompute long-tail metrics from compact raw delay arrays (not the full table).
    delay=np.concatenate(list(values.values()));del values
    minimal=pd.DataFrame({'arr_delay':delay,'arr_delay_min':np.maximum(delay,0)})
    profile=tail.percentile_profile(minimal);severe=tail.severe_shares(minimal);burden=tail.delay_burden(minimal);concentration=tail.lorenz(minimal)
    profile.to_csv(config.TABLE_DIR/'percentile_profile.csv',index=False);concentration['curve'].to_csv(config.TABLE_DIR/'lorenz_curve.csv',index=False)
    models.save_metrics({'mode':config.mode(),'percentiles':profile.to_dict(orient='records'),'severe':severe,'burden':burden,
                        'concentration':{k:v for k,v in concentration.items() if k!='curve'},
                        'scope':'fresh full-source completed delays; rotation analysis built separately'},'tail')
    viz.fig_lorenz(concentration)
    print('Fresh source, cause and tail outputs completed',flush=True)
    return matrix
