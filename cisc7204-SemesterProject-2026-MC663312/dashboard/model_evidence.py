"""Fixed holdout evidence, separate from filterable observed statistics."""
import json
from dash import html, dcc
import plotly.graph_objects as go
from team01 import config


def build():
    path=config.METRIC_DIR/'models.json'
    if not path.exists():
        return html.Div()
    risk=json.loads(path.read_text(encoding='utf-8')).get('risk',{})
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
    ],className='band model-evidence')


def temporal_evidence():
    path=config.METRIC_DIR/'temporal_validation.json'
    if not path.exists():
        return html.Div()
    payload=json.loads(path.read_text(encoding='utf-8'))
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
