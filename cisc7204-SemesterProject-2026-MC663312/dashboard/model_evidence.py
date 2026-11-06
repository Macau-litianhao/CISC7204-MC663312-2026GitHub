"""Fixed holdout evidence, separate from filterable observed statistics."""

from team01 import models as metric_store
import json
from dash import html, dcc
import plotly.graph_objects as go
from team01 import config


def build():
    path=config.METRIC_DIR/'models.json'
    if not path.exists():
        return html.Div()
    payload=metric_store.load_metrics(path.stem)
    risk=payload.get('risk',{})
    scores=risk.get('models',{})
    rows=[]
    for key,label in [('constant_train_rate','Constant training rate'),('logistic','Logistic regression'),('gradient_boosting','Gradient boosting')]:
        if key in scores:
            m=scores[key]
            rows.append(html.Tr([html.Td(label),html.Td(f"{m['roc_auc']:.3f}"),
                html.Td(f"{m.get('average_precision',m.get('pr_auc',0)):.3f}"),html.Td(f"{m['brier']:.4f}")]))
    if not rows:
        return html.Div()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Perfect calibration',line={'color':'#8894A0','dash':'dot'}))
    extent=.15
    for key,label in [('logistic','Logistic'),('gradient_boosting','Gradient boosting')]:
        points=risk.get('calibration',{}).get(key,[])
        if points:
            extent=max(extent,max(max(p['predicted'],p['observed']) for p in points)*1.15)
            fig.add_trace(go.Scatter(x=[p['predicted'] for p in points],y=[p['observed'] for p in points],mode='lines+markers',name=label))
    extent=min(1,extent)
    fig.update_layout(height=330,margin={'l':55,'r':20,'t':15,'b':75},paper_bgcolor='white',plot_bgcolor='white',
        legend={'orientation':'h','y':-0.25},xaxis={'title':'Mean predicted probability','range':[0,extent],'tickformat':'.0%'},
        yaxis={'title':'Observed frequency','range':[0,extent],'tickformat':'.0%'})
    split=risk.get('split',{})
    base=risk.get('test_base_rate')
    prevalence=f"{base:.1%}" if base is not None else 'not recorded'
    return html.Section([
        html.H2('Model evidence · fixed temporal holdout',className='band-title'),
        html.P(f"Test starts {split.get('actual_test_start','not recorded')}; n={risk.get('test_rows',0):,}; "
               f"observed 60+ minute frequency {prevalence}. This reference does not follow page filters.",className='band-note'),
        html.Table([html.Thead(html.Tr([html.Th(x) for x in ['Model','ROC AUC ↑','Average precision ↑','Brier error ↓']])),html.Tbody(rows)],className='evidence-table'),
        html.P('The constant baseline uses the training frequency. Calibration bins are descriptive holdout checks, not fitted recalibration.',className='band-note'),
        dcc.Graph(figure=fig,config={'displayModeBar':False,'responsive':True}),
        temporal_evidence(),
        inference_evidence(payload),
        supplementary_evidence(),
    ],className='band model-evidence')


def temporal_evidence():
    path=config.METRIC_DIR/'temporal_validation.json'
    if not path.exists():
        return html.Div()
    payload=metric_store.load_metrics(path.stem)
    rows=[]
    for item in payload.get('results',[]):
        if item['model']!='gradient_boosting':
            continue
        rows.append(html.Tr([html.Td(str(item['test_year'])),html.Td(f"{item['roc_auc']:.3f}"),
            html.Td(f"{item['brier_gain']:+.5f}"),
            html.Td(f"{item['gain_ci_low']:+.5f} to {item['gain_ci_high']:+.5f}")]))
    return html.Details([
        html.Summary('Across-year robustness: performance changes under disruption'),
        html.P('Expanding-window tests train only on earlier years. This separate specification omits year/COVID controls; parameters are fixed, with no tuning on these folds.',className='band-note'),
        html.Table([html.Thead(html.Tr([html.Th(x) for x in ['Test year','Boosting AUC','Brier gain','95% weekly-block interval']])),html.Tbody(rows)],className='evidence-table'),
        html.P('Positive gain means less error than a constant training-rate baseline. In 2020 the model has negative gain despite AUC above 0.5: ranking is not probability reliability. Intervals condition on the fixed sample and fitted models.',className='band-note'),
    ],className='temporal-evidence')


def inference_evidence(payload):
    """Conditional associations remain separate from predictive accuracy."""
    names={'dep_hour':'Departure hour','month':'Calendar month','carrier':'Airline','origin':'Origin airport','distance':'Route distance'}
    rows=[html.Tr([html.Td(names.get(item['factor'],item['factor'])),html.Td(f"{item['drop_one_r2']:.5f}")])
          for item in payload.get('conditional_r2',[])]
    if not rows:return html.Div()
    ols=payload.get('ols',{});quantile=payload.get('quantile90',{})
    references=', '.join(f'{names.get(k,k)}: {v}' for k,v in ols.get('reference_levels',{}).items())
    return html.Details([
        html.Summary('Factor associations: reference-coded inference'),
        html.P(f"OLS uses {ols.get('rows',0):,} sampled completed flights, operating-day clustered errors and a full-rank design. Quantile regression targets signed arrival delay (negative = early), n={quantile.get('rows',0):,}.",className='band-note'),
        html.P('Each value is the reduction in R² when that factor is removed while other factors and calendar controls remain. These values are non-additive associations, not causal contributions or a decomposition into percentages.',className='band-note'),
        html.Table([html.Thead(html.Tr([html.Th('Removed factor'),html.Th('Conditional R² decrease')])),html.Tbody(rows)],className='evidence-table'),
        html.P('Coefficient reference levels: '+references,className='band-note'),
        html.P('Coefficient magnitudes with different units are not directly comparable. Quantile coefficients are point estimates; no significance or causal effect is claimed.',className='band-note'),
    ],className='temporal-evidence')


def supplementary_evidence():
    payload=metric_store.load_metrics('supplementary')
    if not payload:return html.Div()
    excluded=metric_store.load_metrics('attribution').get('quality_exclusions',{})
    return html.Details([
        html.Summary('Data-quality and sensitivity checks'),
        html.P(f"Cause analysis excludes {int(excluded.get('cause_incomplete_or_invalid',0)):,} incomplete records and {int(excluded.get('cause_unreconciled',0)):,} complete records whose cause minutes do not reconcile. Unknown causes are not imputed as zero.",className='band-note'),
        html.P('The full observed delay distribution remains primary. Upper-tail trimming and winsorization are sensitivity checks, not automatic outlier removal. Common-support airline comparisons use the same stratum weights across airlines and remain descriptive.',className='band-note'),
        html.Table([html.Thead(html.Tr([html.Th('Tail specification'),html.Th('Mean arrival delay'),html.Th('Completed flights')])),html.Tbody([
            html.Tr([html.Td(item['specification']),html.Td(f"{item['mean']:+.2f} min"),html.Td(f"{item['flights']:,}")])
            for item in payload.get('extreme_sensitivity',[])])],className='evidence-table'),
    ],className='temporal-evidence')
