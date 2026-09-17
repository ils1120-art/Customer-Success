"""outputs/aurelle-brief-set.md -> 문서별 HTML 3개.
   테마: brandbrief.io (연그레이 배경 / 네온 액센트 / 헤비 그로테스크)"""
import re, html, markdown

SRC = 'outputs/aurelle-brief-set.md'
TPL = 'tools/brief-template.html'

META = [
    dict(file='01-campaign-plan.html',  badge='문서 1 — 내부용',
         intro='콘셉트 확정부터 성과 측정까지 캠페인 전 과정을 담은 내부 운영 문서입니다. 마케팅팀과 대행사가 함께 봅니다.'),
    dict(file='02-creator-brief.html',  badge='문서 2 — 크리에이터 배포용',
         intro='크리에이터에게 전달하는 1~2페이지 브리프입니다. 배정받은 콘셉트 1개만 담아 보냅니다.'),
    dict(file='03-product-brief.html',  badge='문서 3 — 크리에이터 배포용',
         intro='크리에이터가 제품을 이해하기 위한 문서입니다. 전성분과 임상 결과를 확보한 뒤 배포합니다.'),
]

src = open(SRC).read()
parts = re.split(r'(?m)^# (문서 \d+ — .+)$', src)
docs = [dict(title=parts[i].strip(), md=parts[i+1]) for i in range(1, len(parts), 2)]
assert len(docs) == len(META), '문서 수가 %d개입니다' % len(docs)

def clean(md):
    if md.lstrip().startswith('---'):
        md = re.sub(r'(?m)^---\s*$', '', md, count=1)
    md = re.sub(r'(?m)^  (?=[-*+] |\d+\. )', '    ', md)   # 4-space nested lists
    md = md.replace('### ✿ ', '### ')                  # notion flower marker
    return md.strip()

def render(md_text):
    h = markdown.markdown(clean(md_text), extensions=['tables', 'sane_lists'])
    h = re.sub(r'\(입력 필요([^)]*)\)',
               lambda m: '<span class="todo">입력 필요%s</span>' % html.escape(m.group(1)), h)
    h = re.sub(r'\(TO BE PROVIDED([^)]*)\)',
               lambda m: '<span class="todo">TO BE PROVIDED%s</span>' % html.escape(m.group(1)), h)
    h = re.sub(r'<table>.*?</table>', lambda m: '<div class="scroll">%s</div>' % m.group(0), h, flags=re.S)
    return h

def headings(md_text):
    out = []
    for line in clean(md_text).split('\n'):
        m = re.match(r'^### (.+)$', line) or re.match(r'^## (.+)$', line)
        if m:
            out.append(m.group(1).strip())
    return out

def with_ids(md_text, di):
    h, n = render(md_text), [0]
    def rep(m):
        sid = 'd%ds%d' % (di, n[0]); n[0] += 1
        return '<%s id="%s">%s</%s>' % (m.group(1), sid, m.group(2), m.group(1))
    return re.sub(r'<(h2|h3)>(.*?)</\1>', rep, h, flags=re.S)

tpl = open(TPL).read()
short = [d['title'].split('—')[1].strip() for d in docs]

for i, d in enumerate(docs):
    body = with_ids(d['md'], i)
    toc = ''.join('<li><a href="#d%ds%d">%s</a></li>' % (i, j, html.escape(t))
                  for j, t in enumerate(headings(d['md'])))
    nav = ''.join('<a href="%s"%s>%s</a>' % (META[j]['file'], ' aria-current="page"' if j == i else '',
                                             html.escape(short[j]))
                  for j in range(len(docs)))
    nxt = (i + 1) % len(docs)
    todo = body.count('class="todo"')
    page = (tpl
        .replace('{{TITLE}}', html.escape('AURELLE — ' + short[i]))
        .replace('{{ANN_B}}', html.escape(short[nxt]))
        .replace('{{ANN}}', '노션 업로드 전 초안 · 브랜드 데이터 확보 후 확정')
        .replace('{{NAV}}', nav)
        .replace('{{NEXT_HREF}}', META[nxt]['file'])
        .replace('{{NEXT_LABEL}}', html.escape(short[nxt]))
        .replace('{{BADGE}}', html.escape(META[i]['badge']))
        .replace('{{H1}}', html.escape(short[i]))
        .replace('{{SUB}}', 'AURELLE Glow Drop Serum 미국 캠페인')
        .replace('{{INTRO}}', html.escape(META[i]['intro']))
        .replace('{{TOC}}', toc)
        .replace('{{TODO_NOTE}}', '입력 필요 %d곳' % todo if todo else '입력 항목 없음')
        .replace('{{BODY}}', body))
    open('outputs/' + META[i]['file'], 'w').write(page)
    print('%-26s %6d chars  입력필요 %2d' % (META[i]['file'], len(page), todo))
