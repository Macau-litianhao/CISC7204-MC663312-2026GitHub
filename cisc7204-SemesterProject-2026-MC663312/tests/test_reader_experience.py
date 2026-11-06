import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
import pandas as pd
from reader_layout import hero, timing, scope
from labels import carrier_label, airport_label


def text(node):
    if isinstance(node,(list,tuple)): return ' '.join(text(x) for x in node)
    if hasattr(node,'children'): return text(node.children)
    return str(node or '')


def test_headline_tracks_selection_including_late_median():
    frame=pd.DataFrame({'arr_delay':[30.,60.,90.]})
    content=text(hero(frame))
    assert '60.0 min late' in content and '66.7%' in content
    assert 'early' not in content
    assert 'No flights match' in text(hero(frame.iloc[:0]))


def test_names_preserve_codes_and_support_reader_search():
    assert carrier_label('AA')=='American Airlines (AA)'
    assert 'Los Angeles' in airport_label('LAX') and '(LAX)' in airport_label('LAX')
    assert carrier_label('unknown')=='unknown'


def test_scope_records_all_active_dimensions():
    content=text(scope(2024,['AA'],[7,8],'LAX',545))
    assert all(value in content for value in ['2024','AA','LAX','Jul','Aug','545'])
    assert timing(-6)=='6.0 min early' and timing(0)=='on time'

def test_map_selection_keeps_navigator_and_highlights_only_selected(completed,monkeypatch):
    import data_access as data
    from panels.geo import geo_figure
    from team01 import synth,features,cluster
    reference=synth.make_airport_reference()
    table=features.airport_feature_matrix(completed,reference,min_departures=1)
    # The map needs coordinates only, independently of the exploratory clustering.
    coords=table.reset_index()
    if 'origin' not in coords:
        coords=coords.rename(columns={coords.columns[0]:'origin'})
    monkeypatch.setattr(data,'airport_clusters',lambda:coords)
    chosen=str(completed.origin.iloc[0])
    figure=geo_figure(completed,selected_airport=chosen)
    bubbles=figure.data[1]
    assert len(bubbles.text)>1
    assert list(bubbles.marker.line.width).count(3)==1
    assert bubbles.marker.line.width[list(bubbles.text).index(chosen)]==3
