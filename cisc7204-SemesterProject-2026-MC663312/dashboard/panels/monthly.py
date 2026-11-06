"""Monthly composition and observed severe-delay risk on aligned axes."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_access as data
from team01 import schema,config
from .theme import LEGEND_BELOW,LEGEND_MARGIN,ORANGE_DARK,empty,finish


def monthly_figure(frame):
    if frame.empty:
        return empty('No completed flights in this filter')
    shares=data.composition_by_month(frame)
    profile=data.monthly_profile(frame)
    supported=profile['flights'].fillna(0)>=config.min_hour_flights()
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.17,row_heights=[.65,.35])
    for cause in schema.CAUSE_COLUMNS:
        if cause in shares:
            fig.add_trace(go.Bar(x=list(shares.index),y=shares[cause],name=schema.CAUSE_LABELS[cause],
                marker_color=schema.CAUSE_COLORS[cause],
                hovertemplate='%{y:.1%}<extra>'+schema.CAUSE_LABELS[cause]+'</extra>'),row=1,col=1)
    fig.add_trace(go.Bar(x=profile.index,y=profile['share_60'].where(supported),name='60+ min risk',
        marker_color=ORANGE_DARK,showlegend=False,customdata=profile['flights'],
        hovertemplate='%{y:.1%} delayed 60+ min<br>n=%{customdata:,}<extra>Observed risk</extra>'),row=2,col=1)
    if shares.empty:
        fig.add_annotation(text='No reported cause minutes',x=.5,y=.85,xref='paper',yref='paper',showarrow=False)
    fig.update_layout(legend=LEGEND_BELOW,barmode='stack',bargap=.18)
    result=finish(fig,margin=LEGEND_MARGIN)
    result.update_xaxes(tickmode='array',tickvals=list(range(1,13)),ticktext=schema.MONTH_LABELS)
    result.update_yaxes(title_text='Cause share',range=[0,1],tickformat='.0%',row=1,col=1)
    result.update_yaxes(title_text='60+ share',rangemode='tozero',tickformat='.0%',row=2,col=1)
    return result
