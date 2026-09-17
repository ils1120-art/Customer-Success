import re, markdown, html, json, io

src = open('outputs/aurelle-brief-set.md').read()

# split into cover + 3 documents
parts = re.split(r'(?m)^# (문서 \d+ — .+)$', src)
cover_md = parts[0]
docs = []
for i in range(1, len(parts), 2):
    docs.append({'title': parts[i].strip(), 'md': parts[i+1]})

def clean(md):
    md = re.sub(r'(?m)^---\s*$', '', md, count=1) if md.lstrip().startswith('---') else md
    # python-markdown wants 4-space indents for nested lists
    md = re.sub(r'(?m)^  (?=[-*+] |\d+\. )', '    ', md)
    # the flower marker is Notion styling; the HTML has its own hierarchy
    md = md.replace('### \u273f ', '### ')
    return md.strip()

md_ext = ['tables', 'sane_lists']

def render(md_text):
    h = markdown.markdown(clean(md_text), extensions=md_ext)
    # tag the (입력 필요) / (TO BE PROVIDED) placeholders
    h = re.sub(r'\(입력 필요([^)]*)\)', lambda m: '<span class="todo">입력 필요%s</span>' % html.escape(m.group(1)), h)
    h = re.sub(r'<table>.*?</table>', lambda m: '<div class="scroll">%s</div>' % m.group(0), h, flags=re.S)
    return h

# cover: drop the H1, keep table + note
cover_md_body = re.sub(r'(?m)^# .+$', '', cover_md, count=1)
cover_html = render(cover_md_body)

def outline(md_text):
    items = []
    for line in clean(md_text).split('\n'):
        m2 = re.match(r'^## (.+)$', line)
        m3 = re.match(r'^### (?:\u273f )?(.+)$', line)
        if m3: items.append(('h3', m3.group(1).strip()))
        elif m2: items.append(('h2', m2.group(1).strip()))
    return items

def slug(i, j): return 'd%ds%d' % (i, j)

# inject ids into rendered html headings, in document order
def with_ids(md_text, di):
    h = render(md_text)
    k = [0]
    def rep(m):
        tag, inner = m.group(1), m.group(2)
        txt = re.sub('<[^>]+>', '', inner)
        if tag == 'h3' and '✿' not in txt and True:
            pass
        sid = slug(di, k[0]); k[0] += 1
        return '<%s id="%s">%s</%s>' % (tag, sid, inner, tag)
    h = re.sub(r'<(h2|h3)>(.*?)</\1>', rep, h, flags=re.S)
    return h

doc_html = [with_ids(d['md'], i) for i, d in enumerate(docs)]
outlines = [outline(d['md']) for d in docs]

nav = []
for i, d in enumerate(docs):
    links = []
    for j, (lvl, txt) in enumerate(outlines[i]):
        links.append('<a class="nl %s" href="#%s">%s</a>' % (lvl, slug(i, j), html.escape(txt)))
    nav.append(''.join(links))

tabs = ''.join(
    '<button class="tab%s" data-i="%d"><span class="tn">%02d</span>%s</button>'
    % (' on' if i == 0 else '', i, i+1, html.escape(d['title'].split('—')[1].strip()))
    for i, d in enumerate(docs))

panes = ''.join(
    '<article class="doc%s" data-i="%d"><header class="dh"><span class="dn">%s</span><h1>%s</h1></header>%s</article>'
    % (' on' if i == 0 else '', i, html.escape(d['title'].split('—')[0].strip()),
       html.escape(d['title'].split('—')[1].strip()), doc_html[i])
    for i, d in enumerate(docs))

navs = ''.join('<div class="navset%s" data-i="%d">%s</div>' % (' on' if i==0 else '', i, nav[i]) for i in range(len(docs)))

TPL = open('tools/brief-template.html').read()
out = (TPL.replace('<!--TABS-->', tabs)
          .replace('<!--NAV-->', navs)
          .replace('<!--COVER-->', cover_html)
          .replace('<!--PANES-->', panes))
open('outputs/brief-set.html','w').write(out)
print('written', len(out), 'chars /', len(docs), 'docs')
