"""Reader-first composition; analytical builders remain shared with exports."""
from dash import html, dcc
import data_access as data
import captions
import labels
from team01 import schema


def timing(value):
    if abs(value) < .05:
        return 'on time'
    return f'{abs(value):.1f} min ' + ('early' if value < 0 else 'late')


def hero(frame):
    if frame.empty:
        return [html.H2('No flights match these filters.'), html.P('Change the year, carrier, airport or months to continue.')]
    delay = frame['arr_delay']
    return [html.Div('THE QUESTION · WHAT DOES A DELAY AVERAGE HIDE?', className='eyebrow'),
            html.H2('Read the typical flight and the long-delay risk together.'),
            html.Div([
                html.Div([html.Strong(timing(float(delay.median()))), html.Span('Median arrival relative to schedule')]),
                html.Div([html.Strong(f'{(delay >= 60).mean():.1%}'), html.Span('of completed flights arrive 60+ minutes late')]),
            ], className='hero-facts'),
            html.P(f'Current selection · {len(frame):,} sampled completed flights. Descriptive patterns, not a forecast for your flight. Cancelled and diverted flights excluded.', className='hero-note')]


def scope(year, carriers, months, airport, count):
    low, high = months or [1,12]
    carrier = ', '.join(carriers) if carriers else 'All carriers'
    place = labels.airport_short(airport) if airport else 'All airports'
    return [html.Span(f'{year if year != "all" else "All years"} · {carrier} · {place} · {schema.MONTH_LABELS[int(low)-1]}–{schema.MONTH_LABELS[int(high)-1]} · n={count:,}'), html.A('Change filters ↑', href='#filters')]


def build(meta):
    import layouts as parts
    import model_evidence
    opening = data.apply_filters('all', None, list(range(1,13)))
    cards = parts._grid(captions.findings(opening, opening)).children
    method = parts._method(meta)
    def chapter(identifier, title, note, indices):
        return html.Section([parts._band_head(title,note), html.Div([cards[i] for i in indices],className='grid')],id=identifier,className='reader-chapter')
    glossary = [('Median / 中位数','The middle arrival delay: half of flights arrive earlier, half later. Negative minutes mean early arrival.'),
                ('90th percentile / 第90百分位','90% of completed flights arrive at or before this many minutes relative to schedule; 10% arrive later.'),
                ('Reported causes / 上报延误原因','Shares use reported cause minutes for arrivals at least 15 minutes late, not shares of all flights. NAS means National Aviation System.'),
                ('Gini, PCA and ARI','Gini summarises concentration; PCA projects many features onto two axes; ARI compares group assignments. These are exploratory tools.'),
                ('AUC and Brier','AUC measures ranking; Brier measures probability error (lower is better). Neither establishes causation.')]
    return html.Div([
        dcc.Location(id='url',refresh=False),dcc.Store(id='drill-airport'),
        html.A('Skip to filters',href='#filters',className='skip-link'),
        parts._fixture_banner(meta),parts._header(meta),
        dcc.Loading(html.Section(hero(opening),id='hero-content',className='reader-hero',**{'aria-live':'polite'}),delay_show=220,type='circle'),
        html.Div([
            html.Nav([html.A(text,href='#'+target) for target,text in [('hero-content','Overview'),('filters','Explore'),('time-patterns','When'),('places','Where & carriers'),('deep-analysis','Deep dive'),('method','Method')]],className='reader-nav',**{'aria-label':'Page sections'}),
            dcc.Loading(html.Div(scope('all',[],[1,12],None,len(opening)),id='current-scope',className='current-scope',**{'aria-live':'polite'}),delay_show=220,type='circle'),
        ],className='reader-sticky'),
        html.Section([parts._band_head('Explore the sample','Search carrier names, airport names, cities or codes. Changes update the headline and sample views; exceptions are labelled on each chart.'),parts._filters(meta)],id='filters',className='reader-chapter'),
        html.Div([parts.kpi_card(item) for item in data.kpis(opening)],id='kpi-strip',className='kpi-strip'),
        parts._sample_note(meta),
        html.Details([html.Summary('More findings for this selection'),parts._findings()],className='reader-disclosure'),
        chapter('arrival-patterns','01 · Start with the distribution and reported causes','Read the typical arrival first, then the composition of reported delay minutes. A cause share is not a probability of delay.',[3,0]),
        chapter('time-patterns','02 · When does observed risk change?','Compare months and local departure hours. These associations do not isolate weather, routes or operating conditions.',[1,2]),
        chapter('places','03 · Where, and with which carrier?','Click a map bubble to select an airport; click it again to clear. An orange outline marks the selected airport. The searchable airport filter is the keyboard alternative.',[6,7]),
        html.Section([html.H2('04 · Investigate the evidence'),html.Details([html.Summary('Deep dive: concentration, airport groups and model validation'),html.Div([cards[5],cards[4]],className='grid'),html.Span('Fixed analytical samples · model results do not follow page filters',className='scope-badge'),model_evidence.build()],className='reader-disclosure')],id='deep-analysis',className='reader-chapter'),
        html.Section([parts._band_head('Method, scope and limits','Compare like with like. These are descriptive results for completed flights, not causal explanations or individual predictions.'),method.children[1],html.Details([html.Summary('Data provenance and analytical limits'),method.children[2]],className='reader-disclosure'),html.Details([html.Summary('Plain-language glossary · 术语帮助'),html.Dl([item for term,meaning in glossary for item in (html.Dt(term),html.Dd(meaning))])],className='reader-disclosure')],id='method',className='method'),
        html.Footer([html.Span('Source: '+parts.SOURCE_LINE),html.A('Back to overview ↑',href='#hero-content')],className='app-footer'),
    ],className='app-shell')
