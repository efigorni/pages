"""Extract slide text + speaker notes from the downloaded shefi decks into markdown.

    uv run --with python-pptx python3 tools/extract_pptx.py [--out DIR]

Reads sources/manifest.json, writes sources/text/<grade>/<deck>.md and sources/index.json
(with --out: the same layout under DIR). Lesson agents read sources/text while this runs, so each
file is replaced atomically, and only when its content changed.

Per slide:
- the header, with flags: hidden, images, videos, SmartArt, charts;
- the text boxes the slide shows from its layout and master (a summary slide's "מה למדנו היום?" lives there);
- the text of every shape on the slide (groups and tables included);
- the text of each SmartArt diagram, then each chart ("(תרשים) …");
- links: hyperlinks and online videos;
- the speaker notes.
SmartArt text has no marker line of its own (the header flag marks it), so a heading and the SmartArt items under
it stay contiguous for the verbatim check.
"""
import argparse, json, os, re, shutil, sys, tempfile, zipfile
from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
G = {"כיתה ו'": "6", "כיתה ז'": "7", "כיתה ח'": "8", "כיתה ט'": "9"}
NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'dgm': 'http://schemas.openxmlformats.org/drawingml/2006/diagram',
    'dsp': 'http://schemas.microsoft.com/office/drawing/2008/diagram',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
DIAGRAM_URI = NS['dgm']
CHART_URI = NS['c']


def q(tag):
    p, t = tag.split(':')
    return f'{{{NS[p]}}}{t}'


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


# ----------------------------------------------------------------------------- SmartArt and charts
# python-pptx exposes neither: their text lives in parts of their own, reached from the slide's graphic frames.

def body_text(el):
    """The <a:p> paragraphs under `el` (runs and fields; <a:br/> breaks the line), one line each."""
    if el is None:
        return ''
    paras = []
    for p in el.iterfind('a:p', NS):
        s = ''
        for ch in p:
            tag = etree.QName(ch).localname
            if tag in ('r', 'fld'):
                s += ch.findtext('a:t', default='', namespaces=NS)
            elif tag == 'br':
                s += '\n'
        paras.append(s)
    return '\n'.join(l.strip() for l in clean('\n'.join(paras)).split('\n') if l.strip())


def related_xml(slide, rid):
    try:
        return etree.fromstring(slide.part.related_part(rid).blob)
    except (KeyError, ValueError, etree.XMLSyntaxError):
        return None


def same_row(a, b):
    """Two text boxes (x, y, cx, cy) overlap vertically by at least half of the shorter one."""
    overlap = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return overlap >= 0.5 * max(1, min(a[3], b[3]))


def reading_order(blocks):
    """The data model keeps the text-pane order. A layout drawn left to right in rows (a block grid
    without "right to left") is read here right to left, row by row; every other layout — lists,
    cycles, pyramids, RTL grids — is read in text-pane order."""
    if len(blocks) < 2 or any(b['box'] is None for b in blocks):
        return blocks
    rows = [[blocks[0]]]
    for b in blocks[1:]:
        if same_row(rows[-1][-1]['box'], b['box']):
            rows[-1].append(b)
        else:
            rows.append([b])
    ltr_rows = (any(len(r) > 1 for r in rows)
                and all(all(r[i]['box'][0] < r[i + 1]['box'][0] for i in range(len(r) - 1)) for r in rows)
                and all(rows[i][0]['box'][1] < rows[i + 1][0]['box'][1] and not same_row(rows[i][0]['box'], rows[i + 1][0]['box'])
                        for i in range(len(rows) - 1)))
    return [b for r in rows for b in reversed(r)] if ltr_rows else blocks


def smartart_blocks(slide, gd):
    """One SmartArt diagram (ppt/diagrams/dataN.xml): a block per top-level item — its text, then its
    sub-items' — in reading order. Positions come from the drawing part (drawingN.xml); with no data-model
    text, the drawing's text is used as is."""
    ri = gd.find('dgm:relIds', NS)
    data = related_xml(slide, ri.get(q('r:dm'))) if ri is not None else None
    if data is None:
        return []
    pts = {p.get('modelId'): p for p in data.iterfind('dgm:ptLst/dgm:pt', NS)}
    kids, shown_by = {}, {}
    for c in data.iterfind('dgm:cxnLst/dgm:cxn', NS):
        kind = c.get('type', 'parOf')
        if kind == 'parOf':
            kids.setdefault(c.get('srcId'), []).append((int(c.get('srcOrd') or 0), c.get('destId')))
        elif kind == 'presOf':
            shown_by.setdefault(c.get('destId'), set()).add(c.get('srcId'))
    for m, p in pts.items():
        ps = p.find('dgm:prSet', NS)
        if p.get('type') == 'pres' and ps is not None and ps.get('presAssocID'):
            shown_by.setdefault(m, set()).add(ps.get('presAssocID'))

    def subtree(m, seen):
        if m in seen:
            return
        seen.add(m)
        yield m
        for _, d in sorted(kids.get(m, [])):
            yield from subtree(d, seen)

    blocks, seen = [], set()
    for doc in [m for m, p in pts.items() if p.get('type') == 'doc']:
        for _, top in sorted(kids.get(doc, [])):
            ids = [m for m in subtree(top, seen) if m in pts and pts[m].get('type', 'node') in ('node', 'asst')]
            text = '\n'.join(t for t in (body_text(pts[m].find('dgm:t', NS)) for m in ids) if t)
            if text:
                blocks.append({'ids': set(ids), 'text': text, 'box': None})

    drawing = None
    ext = data.find('dgm:extLst//dsp:dataModelExt', NS)
    if ext is not None and ext.get('relId'):
        drawing = related_xml(slide, ext.get('relId'))
    if drawing is not None:
        for sp in drawing.iter(q('dsp:sp')):
            if not body_text(sp.find('dsp:txBody', NS)):
                continue
            xf = sp.find('dsp:txXfrm', NS)
            if xf is None:
                xf = sp.find('dsp:spPr/a:xfrm', NS)
            off, size = (xf.find('a:off', NS), xf.find('a:ext', NS)) if xf is not None else (None, None)
            if off is None or size is None:
                continue
            box = tuple(int(v) for v in (off.get('x'), off.get('y'), size.get('cx'), size.get('cy')))
            nodes = shown_by.get(sp.get('modelId'), set())
            for b in blocks:
                if nodes & b['ids'] and (b['box'] is None or (box[1], -box[0]) < (b['box'][1], -b['box'][0])):
                    b['box'] = box
        if not blocks:
            return [t for t in (body_text(sp.find('dsp:txBody', NS)) for sp in drawing.iter(q('dsp:sp'))) if t]
    return [b['text'] for b in reading_order(blocks)]


def num(v, code=''):
    try:
        f = float(v)
    except ValueError:
        return v
    if '%' in code:
        f *= 100
    s = str(int(f)) if f.is_integer() else f'{f:g}'
    return s + '%' if '%' in code else s


def chart_blocks(slide, gd):
    """One chart (ppt/charts/chartN.xml): its title, then a line per series — the series name, and each
    category with its value."""
    ch = gd.find('c:chart', NS)
    cs = related_xml(slide, ch.get(q('r:id'))) if ch is not None else None
    if cs is None:
        return []
    lines = []
    title = cs.find('c:chart/c:title', NS)
    if title is not None:
        rich = title.find('c:tx/c:rich', NS)
        t = body_text(rich) if rich is not None else clean(' '.join(v.text or '' for v in title.iterfind('.//c:v', NS)))
        if t:
            lines.append(t)
    for ser in cs.iter(q('c:ser')):
        name = clean(' '.join(v.text or '' for v in ser.iterfind('c:tx//c:v', NS)))
        cat = ser.find('c:cat', NS)
        if cat is None:
            cat = ser.find('c:xVal', NS)
        cats = {}
        if cat is not None:
            lvl = cat.find('.//c:lvl', NS)
            for pt in (lvl if lvl is not None else cat).iter(q('c:pt')):
                cats.setdefault(int(pt.get('idx') or 0), clean(pt.findtext('c:v', default='', namespaces=NS)))
        val = ser.find('c:val', NS)
        if val is None:
            val = ser.find('c:yVal', NS)
        items = []
        if val is not None:
            code = val.findtext('.//c:formatCode', default='', namespaces=NS)
            for pt in val.iter(q('c:pt')):
                v = num(pt.findtext('c:v', default='', namespaces=NS), code)
                items.append(f"{cats.get(int(pt.get('idx') or 0), '')} {v}".strip())
        if name or items:
            lines.append((f'{name}: ' if name else '') + ' · '.join(items))
    return ['\n'.join(lines)] if lines else []


def graphic_blocks(slide):
    """[(kind, blocks)] for the slide's SmartArt diagrams and charts, in shape order (groups included)."""
    out = []
    for gd in slide._element.iter(q('a:graphicData')):
        if any(a.tag == q('mc:Fallback') for a in gd.iterancestors()):
            continue
        uri = gd.get('uri', '')
        if uri == DIAGRAM_URI:
            kind, blocks = 'smartart', smartart_blocks(slide, gd)
        elif uri == CHART_URI:
            kind, blocks = 'chart', chart_blocks(slide, gd)
        else:
            continue
        if blocks:
            out.append((kind, blocks))
    return out


def layout_text(slide):
    """Text boxes the slide shows from its master and layout. Placeholders there are prompts and never show;
    "hide background graphics" (showMasterSp="0") hides the rest — on the slide for both, on the layout for the master."""
    if slide._element.get('showMasterSp') == '0':
        return []
    layout = slide.slide_layout
    sources = ([layout.slide_master] if layout._element.get('showMasterSp') != '0' else []) + [layout]
    out = []
    for src in sources:
        for sp in src._element.cSld.spTree.iter(q('p:sp')):
            if sp.find(f".//{q('p:ph')}") is not None or any(a.tag == q('mc:Fallback') for a in sp.iterancestors()):
                continue
            t = body_text(sp.find('p:txBody', NS))
            if t:
                out.append(t)
    return out


def extract(path):
    prs = open_prs(path)
    slides = []
    for i, s in enumerate(prs.slides, 1):
        acc, media = layout_text(s), {'img': 0, 'video': 0, 'links': set()}
        walk(s.shapes, acc, media)
        for rel in s.part.rels.values():
            if not rel.is_external:
                continue
            online_media = rel.reltype.rsplit('/', 1)[-1] in ('video', 'media', 'audio')
            if 'hyperlink' in rel.reltype or (online_media and re.match(r'https?://', rel.target_ref)):
                media['links'].add(rel.target_ref)
        notes = ''
        if s.has_notes_slide:
            notes = clean(s.notes_slide.notes_text_frame.text if s.notes_slide.notes_text_frame else '')
        hidden = s._element.get('show') == '0'
        slides.append({'n': i, 'text': acc, 'graphics': graphic_blocks(s), 'notes': notes, 'img': media['img'],
                       'video': media['video'], 'links': sorted(media['links']), 'hidden': hidden})
    return slides


def render(x, slides, words_slides, words_notes):
    out = [f"# {x['title']}\n\n",
           f"- שכבה: {x['grade']}\n- פרק: {x['section']}\n- יחידה: {x.get('unit') or '—'}\n",
           f"- מקור: {x['url']}\n- שקפים: {len(slides)} · מילים בשקפים: {words_slides} · מילים בהערות: {words_notes}\n\n"]
    for s in slides:
        flags = []
        if s['hidden']: flags.append('מוסתר')
        if s['img']: flags.append(f"{s['img']} תמונות")
        if s['video']: flags.append(f"{s['video']} וידאו")
        n_sa = sum(1 for k, _ in s['graphics'] if k == 'smartart')
        n_ch = sum(1 for k, _ in s['graphics'] if k == 'chart')
        if n_sa: flags.append('SmartArt' if n_sa == 1 else f'{n_sa} SmartArt')
        if n_ch: flags.append('תרשים' if n_ch == 1 else f'{n_ch} תרשימים')
        out.append(f"## שקף {s['n']}" + (f"  ({' · '.join(flags)})" if flags else '') + "\n\n")
        for t in s['text']:
            out.append(t + '\n\n')
        for kind, blocks in s['graphics']:
            if kind == 'chart':
                blocks = ['(תרשים) ' + blocks[0]] + blocks[1:]
            out.extend(b + '\n\n' for b in blocks)
        if s['links']:
            out.append('קישורים: ' + ' · '.join(s['links']) + '\n\n')
        if s['notes']:
            out.append('**הערות מנחה:**\n\n' + s['notes'] + '\n\n')
    return ''.join(out)


def write_atomic(path, text):
    """Replace `path` in one step, and only when its content changed. True when written."""
    try:
        with open(path, encoding='utf-8') as f:
            if f.read() == text:
                return False
        mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=f'.{os.path.basename(path)}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', help='write text/<grade>/*.md and index.json under this directory instead of sources/')
    out_root = os.path.abspath(ap.parse_args().out or SRC)
    man = json.load(open(os.path.join(SRC, 'manifest.json'), encoding='utf-8'))
    index, done, changed = [], {}, 0
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
            words_slides = sum(len(' '.join(s['text'] + [b for _, bl in s['graphics'] for b in bl]).split()) for s in slides)
            words_notes = sum(len(s['notes'].split()) for s in slides)
            wrote = write_atomic(os.path.join(out_root, out_rel), render(x, slides, words_slides, words_notes))
            changed += wrote
            done[key] = {'slides': len(slides), 'words_slides': words_slides, 'words_notes': words_notes}
            counts = {k: sum(1 for s in slides for kk, _ in s['graphics'] if kk == k) for k in ('smartart', 'chart')}
            extra = [f'{n} {k}' for k, n in counts.items() if n]
            print(f"ok {key}: {len(slides)} slides, {words_slides}w slides, {words_notes}w notes"
                  + (f" · {', '.join(extra)}" if extra else '') + (' · updated' if wrote else ''), flush=True)
        if key in done:
            index.append({**{k: x[k] for k in ('grade', 'section', 'unit', 'title', 'url')}, 'text': out_rel, **done[key]})
    write_atomic(os.path.join(out_root, 'index.json'), json.dumps(index, ensure_ascii=False, indent=1))
    print(f'{len(done)} decks extracted, {changed} updated, {len(index)} index rows', flush=True)


if __name__ == '__main__':
    main()
