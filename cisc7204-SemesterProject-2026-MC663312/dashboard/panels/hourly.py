"""Aligned hourly views: separate units, shared origin-local hour."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_access as data
from team01 import config, schema
from .theme import ORANGE_DARK, empty, finish


def hourly_figure(frame):
    profile = data.hourly_profile(frame)
    supported = profile['flights'].fillna(0) >= config.min_hour_flights()
    if not supported.any():
        return empty(f'No hour has at least {config.min_hour_flights()} sampled departures')
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15)
    counts = profile['flights'].fillna(0).to_numpy()
    fig.add_trace(go.Bar(x=profile.index, y=profile['share_60'].where(supported),
        name='60+ min share', marker_color=ORANGE_DARK, customdata=counts,
        hovertemplate='%{x}:00 · %{y:.1%}<br>n=%{customdata:,}<extra>Observed severe delay</extra>'),row=1,col=1)
    fig.add_trace(go.Scatter(x=profile.index,y=profile['mean'].where(supported),
        mode='lines+markers', name='Mean delay', line={'color':schema.OKABE_ITO['blue']},
        customdata=counts, connectgaps=False,
        hovertemplate='%{x}:00 · %{y:+.1f} min<br>n=%{customdata:,}<extra>Mean delay</extra>'),row=2,col=1)
    fig.update_layout(showlegend=False)
    result=finish(fig,margin={'l':55,'r':20,'t':12,'b':48})
    result.update_yaxes(title_text='60+ min share',tickformat='.0%',rangemode='tozero',row=1,col=1)
    result.update_yaxes(title_text='Mean (min)',row=2,col=1)
    result.update_xaxes(range=[-0.5,23.5],dtick=3)
    result.update_xaxes(title_text='Scheduled departure hour · origin-local time',row=2,col=1)
    return result
