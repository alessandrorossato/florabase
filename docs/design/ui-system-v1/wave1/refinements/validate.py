"""Validate actual refinement evidence and source digests, not a canonical gate receipt."""
import hashlib
import json
from pathlib import Path

from PIL import Image

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parents[4]
RENDERS = Path('/home/alessandro/.codex/visualizations/2026/10/26/01a178c9-0d81-73f2-96a2-42047619aba9/ui-system-v1/renders/wave1-final')


def validate() -> dict[str, int]:
    entries = json.loads((DOCS / 'captures.json').read_text())
    indexed = {entry['id']: entry for entry in entries}
    assert len(indexed) == len(entries)
    for entry in entries:
        path = RENDERS / f"{entry['id']}.jpg"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], path
        with Image.open(path) as image:
            assert list(image.size) == entry['raster'], path
        assert entry['document'][0] <= entry['viewport'][0], entry['id']
        assert entry['theme'] in ('light', 'dark')
    for width in (1440, 1024, 880, 390):
        for theme in ('light', 'dark'):
            for case in ('dashboard', 'seeds-list', 'seeds-gallery', 'plants-list', 'plants-gallery'):
                item = indexed[f'{case}-{width}-{theme}']
                assert item['viewport'] == [width, 844]
                assert item['theme'] == theme
                assert item['url'].startswith('http://localhost:15279/')
            for domain in ('seeds', 'plants'):
                assert indexed[f'{domain}-overlay-{width}-{theme}']['dialog']
                assert f'{domain}-selection-{width}-{theme}' in indexed
    samples = []
    for theme in ('light', 'dark'):
        for width in (1440, 1024, 880, 390):
            item = indexed[f'dashboard-{width}-{theme}']
            ids = [plant['href'] for plant in item['plants']]
            assert len(ids) == len(set(ids)) == 8
            assert all(href.startswith('#/plants/') for href in ids)
            samples.append(ids)
            if width == 1440:
                assert item['document'] == [1440, 844]
                assert item['dpr'] == item['scale'] == 1
                assert item['dashboard']['footer'] <= 844
                assert item['dashboard']['work'] == 5
                frames = item['dashboard']['frames']
                assert len({frame['x'] for frame in frames}) == 4
                assert len({frame['y'] for frame in frames}) == 2
                assert all(abs(frame['width'] / frame['height'] - 4 / 3) < .001 for frame in frames)
    assert all(sample == samples[0] for sample in samples)
    history = json.loads((DOCS / 'selection-history.json').read_text())
    assert all(history[key]['checked'] == 2 for key in ('before', 'back', 'forward'))
    assert history['reset']['checkboxes'] == 0
    for entry in json.loads((DOCS / 'source-inventory.json').read_text())['files']:
        assert hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
    gallery = json.loads((DOCS / 'gallery-captures.json').read_text())
    current = {entry['id']: entry for entry in gallery}
    assert len(current) == len(gallery) == 37
    for entry in gallery:
        path = RENDERS.parent / 'wave1-gallery' / f"{entry['id']}.jpg"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], path
        with Image.open(path) as image:
            assert list(image.size) == entry['raster'], path
        assert entry['document'][0] <= entry['viewport'][0], entry['id']
        for card in entry['cards']:
            width, height = card['visual']
            if card.get('image'):
                assert abs(width / height - 4 / 3) < .001
            else:
                assert width == height == 48
            assert len(card['actions']) == 3
            assert all(action['width'] >= 44 and action['height'] >= 44 for action in card['actions'])
    for palette in ('botanical', 'herbarium', 'mineral'):
        for appearance in ('light', 'dark'):
            for width in (1440, 1024, 390):
                for context in ('selection', 'long'):
                    entry = current[f'plants-gallery-{context}-{width}-{palette}-{appearance}']
                    assert entry['theme'] == {'palette': palette, 'appearance': appearance}
                    assert entry['viewport'] == [width, 844]
                    if context == 'selection':
                        assert entry['checked'] == len(entry['cards']) == 3
                        assert sum(bool(card.get('image')) for card in entry['cards']) == 1
                    else:
                        assert 'deliberately long synthetic cultivar' in entry['cards'][0]['text']
    return {'captures': len(entries), 'matrix': 40, 'overlay_selection': 32, 'stable_sample': 8, 'final_gallery': len(gallery)}


if __name__ == '__main__':
    print(json.dumps(validate(), sort_keys=True))
