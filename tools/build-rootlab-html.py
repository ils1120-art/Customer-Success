"""outputs/rootlab-brief-set.md -> outputs/rootlab/*.html (문서별 1장)
   테마: ROOTLAB 무드 레퍼런스 (점토·모래 웜 뉴트럴 + 제품별 포인트 컬러)"""
import re, html, os, markdown

SRC = 'outputs/rootlab-brief-set.md'
TPL = 'tools/rootlab-template.html'
OUT = 'outputs/rootlab'

META = [
    dict(file='01-campaign.html',   nav='캠페인',     accent='#6F5B45', accent_d='#C9A87C',
         badge='크리에이터 배포용 · 공통',
         sub='SUNDAY 3-STEP',
         intro='크리에이터 전원이 함께 보는 페이지입니다. 세 제품에 공통인 촬영 조건과 필수 장면, CTA만 담았습니다.'),
    dict(file='02-scaler.html',     nav='스케일러',   accent='#6B4F3A', accent_d='#D0A87F',
         badge='제품 가이드 · STEP 1',
         sub='SCALE-DOWN',
         intro='카올린 퓨리파잉 두피 스케일러를 배정받은 크리에이터가 보는 페이지입니다.'),
    dict(file='03-shampoo.html',    nav='샴푸',       accent='#A57E44', accent_d='#E0BC7E',
         badge='제품 가이드 · STEP 2',
         sub='CLEANSE-DOWN',
         intro='클레이 딥클렌징 샴푸를 배정받은 크리에이터가 보는 페이지입니다.'),
    dict(file='04-treatment.html',  nav='트리트먼트', accent='#77855F', accent_d='#B6C496',
         badge='제품 가이드 · STEP 3',
         sub='PROTEIN-FILL',
         intro='식물성 단백질 트리트먼트를 배정받은 크리에이터가 보는 페이지입니다.'),
]

src = open(SRC).read()
parts = re.split(r'(?m)^# (문서 \d+ — .+)$', src)
docs = [dict(title=parts[i].strip(), md=parts[i + 1]) for i in range(1, len(parts), 2)]
assert len(docs) == len(META), '문서 수가 %d개입니다' % len(docs)


def clean(md):
    md = re.sub(r'(?m)^  (?=[-*+] |\d+\. )', '    ', md)   # 4-space nested lists
    return md.strip()


def render(md_text):
    h = markdown.markdown(clean(md_text), extensions=['tables', 'sane_lists'])
    h = re.sub(r'\(입력 필요([^)]*)\)',
               lambda m: '<span class="todo">입력 필요%s</span>' % html.escape(m.group(1)), h)
    h = re.sub(r'<table>.*?</table>', lambda m: '<div class="scroll">%s</div>' % m.group(0), h, flags=re.S)
    return h


CHK_RE = re.compile(r'<p><strong>([^<]+)</strong></p>\s*<ul>(.*?)</ul>', re.S)


def checkboard(h):
    """'이건 꼭 확인해 주세요' 섹션의 p+ul 묶음을 체크 카드 그리드로."""
    start = h.find('이건 꼭 확인해 주세요')
    if start < 0:
        return h
    start = h.find('</h3>', start) + 5
    end = h.find('<blockquote', start)
    if end < 0:
        end = len(h)
    seg = h[start:end]

    cards = []

    def grab(m):
        cards.append('<div class="chk"><h5>%s</h5><ul>%s</ul></div>'
                     % (m.group(1), m.group(2)))
        return ''
    seg = CHK_RE.sub(grab, seg)
    board = '<div class="check">%s</div>' % ''.join(cards) if cards else ''

    # 키워드 칩 줄
    def chips(m):
        label, rest = m.group(1), m.group(2)
        kind = 'own' if '이 제품만의' in label else 'shared'
        return ('<p class="chips %s"><span class="lbl">%s</span>%s</p>'
                % (kind, html.escape(label.replace('**', '')), rest))
    seg = re.sub(r'<p><strong>(이 제품만의 말|같이 쓰는 말)</strong>(.*?)</p>', chips, seg, flags=re.S)

    return h[:start] + board + seg + h[end:]


LEDE_RE = re.compile('(?:<p>\U0001F3FA .*?</p>\\s*)+', re.S)


def lede(h):
    return LEDE_RE.sub(lambda m: '<div class="lede">%s</div>' % m.group(0), h, count=1)


def headings(md_text):
    return [m.group(1).strip().replace('**','') for m in re.finditer(r'(?m)^#{2,3} (.+)$', clean(md_text))]


def with_ids(h, di):
    n = [0]

    def rep(m):
        sid = 'd%ds%d' % (di, n[0]); n[0] += 1
        return '<%s id="%s">%s</%s>' % (m.group(1), sid, m.group(2), m.group(1))
    return re.sub(r'<(h2|h3)>(.*?)</\1>', rep, h, flags=re.S)


os.makedirs(OUT, exist_ok=True)
tpl = open(TPL).read()

for i, d in enumerate(docs):
    body = with_ids(lede(checkboard(render(d['md']))), i)
    toc = ''.join('<li><a href="#d%ds%d">%s</a></li>' % (i, j, html.escape(t))
                  for j, t in enumerate(headings(d['md'])))
    nav = ''.join('<a href="%s"%s>%s</a>'
                  % (META[j]['file'], ' aria-current="page"' if j == i else '',
                     html.escape(META[j]['nav']))
                  for j in range(len(docs)))
    nxt = (i + 1) % len(docs)
    todo = body.count('class="todo"')
    page = (tpl
            .replace('{{TITLE}}', html.escape('ROOTLAB — ' + META[i]['nav']))
            .replace('{{ACCENT_D}}', META[i]['accent_d'])
            .replace('{{ACCENT}}', META[i]['accent'])
            .replace('{{ANN_B}}', html.escape(META[nxt]['nav']))
            .replace('{{ANN}}', '1차 기획안 기준 초안 · 처방과 임상 확정 후 갱신')
            .replace('{{NAV}}', nav)
            .replace('{{NEXT_HREF}}', META[nxt]['file'])
            .replace('{{NEXT_LABEL}}', html.escape(META[nxt]['nav']))
            .replace('{{BADGE}}', html.escape(META[i]['badge']))
            .replace('{{H1}}', html.escape(META[i]['nav']))
            .replace('{{SUB}}', html.escape(META[i]['sub']))
            .replace('{{INTRO}}', html.escape(META[i]['intro']))
            .replace('{{TOC}}', toc)
            .replace('{{TODO_NOTE}}', '입력 필요 %d곳' % todo if todo else '입력 항목 없음')
            .replace('{{BODY}}', body))
    open(os.path.join(OUT, META[i]['file']), 'w').write(page)
    print('%-20s %6d chars  입력필요 %2d  체크카드 %d'
          % (META[i]['file'], len(page), todo, page.count('class="chk"')))
