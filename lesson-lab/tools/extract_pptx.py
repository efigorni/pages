"""Extract slide text + speaker notes from the downloaded shefi decks into markdown.

    uv run --with python-pptx python3 tools/extract_pptx.py

Reads sources/manifest.json, writes sources/text/<grade>/<deck>.md and sources/index.json.
"""
import json, os, re, shutil, sys, tempfile, zipfile
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
G = {"כיתה ו'": "6", "כיתה ז'": "7", "כיתה ח'": "8", "כיתה ט'": "9"}


def clean(t):
    t = (t or '').replace('\x0b', '\n').replace('\xa0', ' ')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()


def open_prs(path):
    if not path.lower().endswith('.pptm'):
        return Presentation(path)
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, 'deck.pptx')
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == '[Content_Types].xml':
                data = data.replace(b'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml',
                                    b'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml')
            zout.writestr(item, data)
    return Presentation(out)


def walk(shapes, acc, media):
    for sh in shapes:
        try:
            st = sh.shape_type
        except Exception:
            st = None
        if st == MSO_SHAPE_TYPE.GROUP:
            walk(sh.shapes, acc, media)
            continue
        if st == MSO_SHAPE_TYPE.PICTURE:
            media['img'] += 1
        if st == MSO_SHAPE_TYPE.MEDIA:
            media['video'] += 1
        if getattr(sh, 'has_table', False) and sh.has_table:
            for row in sh.table.rows:
                cells = [clean(c.text) for c in row.cells]
                if any(cells):
                    acc.append('| ' + ' | '.join(cells) + ' |')
            continue
        if getattr(sh, 'has_text_frame', False) and sh.has_text_frame:
            t = clean(sh.text_frame.text)
            if t:
                acc.append(t)
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    try:
                        if r.hyperlink and r.hyperlink.address:
                            media['links'].add(r.hyperlink.address)
                    except Exception:
                        pass
        try:
            if sh.click_action and sh.click_action.hyperlink and sh.click_action.hyperlink.address:
                media['links'].add(sh.click_action.hyperlink.address)
        except Exception:
            pass


def extract(path):
    prs = open_prs(path)
    slides = []
    for i, s in enumerate(prs.slides, 1):
        acc, media = [], {'img': 0, 'video': 0, 'links': set()}
        walk(s.shapes, acc, media)
        for rel in s.part.rels.values():
            if 'hyperlink' in rel.reltype and rel.is_external:
                media['links'].add(rel.target_ref)
            if rel.reltype.endswith('/video') or rel.reltype.endswith('/media'):
                media['video'] += 0  # counted via shape type
        notes = ''
        if s.has_notes_slide:
            notes = clean(s.notes_slide.notes_text_frame.text if s.notes_slide.notes_text_frame else '')
        hidden = s._element.get('show') == '0'
        slides.append({'n': i, 'text': acc, 'notes': notes, 'img': media['img'], 'video': media['video'],
                       'links': sorted(media['links']), 'hidden': hidden})
    return slides


def main():
    man = json.load(open(os.path.join(SRC, 'manifest.json'), encoding='utf-8'))
    index, done = [], {}
    for x in man:
        if not x.get('local'):
            continue
        g = G[x['grade']]
        deck = os.path.splitext(os.path.basename(x['local']))[0]
        key = f'{g}/{deck}'
        out_rel = f'text/{g}/{deck}.md'
        if key not in done:
            try:
                slides = extract(os.path.join(SRC, x['local']))
            except Exception as e:
                print(f'FAIL {key}: {e}', flush=True)
                continue
            words_slides = sum(len(' '.join(s['text']).split()) for s in slides)
            words_notes = sum(len(s['notes'].split()) for s in slides)
            os.makedirs(os.path.join(SRC, 'text', g), exist_ok=True)
            with open(os.path.join(SRC, out_rel), 'w', encoding='utf-8') as f:
                f.write(f"# {x['title']}\n\n")
                f.write(f"- שכבה: {x['grade']}\n- פרק: {x['section']}\n- יחידה: {x.get('unit') or '—'}\n")
                f.write(f"- מקור: {x['url']}\n- שקפים: {len(slides)} · מילים בשקפים: {words_slides} · מילים בהערות: {words_notes}\n\n")
                for s in slides:
                    flags = []
                    if s['hidden']: flags.append('מוסתר')
                    if s['img']: flags.append(f"{s['img']} תמונות")
                    if s['video']: flags.append(f"{s['video']} וידאו")
                    f.write(f"## שקף {s['n']}" + (f"  ({' · '.join(flags)})" if flags else '') + "\n\n")
                    for t in s['text']:
                        f.write(t + '\n\n')
                    if s['links']:
                        f.write('קישורים: ' + ' · '.join(s['links']) + '\n\n')
                    if s['notes']:
                        f.write('**הערות מנחה:**\n\n' + s['notes'] + '\n\n')
            done[key] = {'slides': len(slides), 'words_slides': words_slides, 'words_notes': words_notes}
            print(f"ok {key}: {len(slides)} slides, {words_slides}w slides, {words_notes}w notes", flush=True)
        if key in done:
            index.append({**{k: x[k] for k in ('grade', 'section', 'unit', 'title', 'url')}, 'text': out_rel, **done[key]})
    json.dump(index, open(os.path.join(SRC, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(done)} decks extracted, {len(index)} index rows', flush=True)


if __name__ == '__main__':
    main()
