"""outputs/aurelle-brief-set.md -> 노션 페이지 본문 3개 (Notion-flavored Markdown)"""
import re, sys, json

src = open('outputs/aurelle-brief-set.md').read()
parts = re.split(r'(?m)^# (문서 \d+ — .+)$', src)
docs = [dict(title=parts[i].strip(), md=parts[i+1]) for i in range(1, len(parts), 2)]

def esc_cell(t):
    return t.replace('|', '\\|').strip()

def table_block(rows):
    out = ['<table fit-page-width="true" header-row="true">']
    for r in rows:
        out.append('\t<tr>')
        for c in r:
            out.append('\t\t<td>%s</td>' % esc_cell(c))
        out.append('\t</tr>')
    out.append('</table>')
    return '\n'.join(out)

def convert(md):
    md = md.strip()
    if md.startswith('---'):
        md = md[3:].lstrip('\n')
    lines = md.split('\n')
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]

        # pipe table -> notion xml table
        if ln.strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i+1].strip()):
            rows = []
            header = [c.strip() for c in ln.strip().strip('|').split('|')]
            rows.append(header)
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            out.append(table_block(rows))
            continue

        # blockquote run -> callout
        if ln.strip().startswith('> '):
            body = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                body.append(lines[i].strip()[2:].strip())
                i += 1
            out.append('<callout icon="📌" color="gray_bg">')
            for b in body:
                out.append('\t' + b)
            out.append('</callout>')
            continue

        # nested list: 4 spaces -> tab
        if re.match(r'^    (?=[-*+] |\d+\. )', ln):
            out.append('\t' + ln[4:])
            i += 1
            continue

        out.append(ln)
        i += 1
    # collapse 3+ blank lines
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()

bodies = [convert(d['md']) for d in docs]
titles = [d['title'] for d in docs]
json.dump({'titles': titles, 'bodies': bodies}, open('/tmp/claude-0/-home-user-Customer-Success/52b72294-c2ac-56d5-a974-a5d712f97996/scratchpad/notion.json','w'), ensure_ascii=False)
for t, b in zip(titles, bodies):
    print('%-28s %6d chars  tables=%d callouts=%d' % (t, len(b), b.count('<table'), b.count('<callout')))
