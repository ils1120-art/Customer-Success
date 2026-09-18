"""outputs/rootlab-brief-set.md -> outputs/rootlab/*.html (문서별 1장)
   테마: ROOTLAB 무드 레퍼런스 (점토·모래 웜 뉴트럴 + 제품별 포인트 컬러)"""
import re, html, os, markdown

SRC = 'outputs/rootlab-brief-set.md'
TPL = 'tools/rootlab-template.html'
OUT = 'outputs/rootlab'

META = [
    dict(file='00-plan.html',       nav='운영 계획', accent='#5C4B3A', accent_d='#C2A382',
         badge='내부용 · 배포 금지',
         sub='CAMPAIGN PLAN',
         intro='제품 · 소비자 언어 · 그 위에서 내린 결정 · 제품별 콘텐츠 순으로 정리한 내부 문서입니다.',
         internal=True),
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



# ---------- charts ----------
CH_LIGHT, CH_DARK = ('#BE5418', '#00839F'), ('#D96B36', '#17A2BA')

CHART1 = dict(
    title='헤어케어 성분 포화도',
    note='올리브영 헤어케어 · 성분별 제품 수. 클레이와 식물성 단백질은 아직 선도 브랜드가 없습니다.',
    src='기획안 1차 · Trendier AI',
    unit='개', lab='120px',
    legend=[('ROOTLAB이 선택한 성분', 0), ('이미 포화된 성분', 1)],
    rows=[('살리실산', 213, 1, ''), ('덱스판테놀', 168, 1, ''),
          ('클레이', 37, 0, ''), ('식물성 단백질', 28, 0, '')],
)

CHART2 = dict(
    title='경쟁 제품의 최다 부정 리뷰',
    note='각 제품 리뷰에서 가장 많이 반복된 불만과 그 비율. 오른쪽은 이 불만을 겨냥한 ROOTLAB 제품입니다.',
    src='기획안 1차 · Trendier AI',
    unit='%', lab='268px',
    legend=[],
    rows=[('그로우어스 스케일러 · 소금 입자 따가움', 22, 0, 'STEP 1'),
          ('어노브 트리트먼트 · 미끌거리는 잔여감', 18, 0, 'STEP 3'),
          ('닥터포헤어 스케일러 · 모발 뻣뻣함', 18, 0, 'STEP 1'),
          ('어노브 샴푸 · 오후 떡짐', 15, 0, 'STEP 2'),
          ('피노 헤어마스크 · 무거운 영양감', 14, 0, 'STEP 3'),
          ('아로마티카 샴푸 · 거품 부족', 10, 0, 'STEP 2'),
          ('쿤달 트리트먼트 · 지속력 부족', 9, 0, '—')],
)


CHART3 = dict(
    title='가격대별 누적 리뷰 — 청량감과 거품',
    note='같은 키워드도 가격대에 따라 무게가 다릅니다. 청량감은 2만원 이하에 몰려 있고, 거품은 전 구간의 기본 기대치입니다.',
    src='올리브영 헤어케어 2025.09–2026.08 · Trendier AI',
    unit='건', lab='150px',
    legend=[('2만원 이하 (우리 구간)', 0), ('2만~5만원', 1)],
    rows=[('청량감 · 2만원 이하', 17944, 0, ''), ('청량감 · 2만~5만원', 8240, 1, ''),
          ('거품 · 2만원 이하', 39202, 0, ''), ('거품 · 2만~5만원', 52787, 1, '')],
)


def chart(c):
    top = max(r[1] for r in c['rows'])
    bars = []
    for label, val, slot, tag in c['rows']:
        pct = val / top * 100
        bars.append(
            '<div class="vz-row" tabindex="0" data-tip="%s — %s%s">'
            '<div class="vz-lab">%s</div>'
            '<div class="vz-track"><div class="vz-bar s%d" style="width:%.1f%%"></div>'
            '<span class="vz-val">%s%s</span></div>'
            '<div class="vz-tag">%s</div></div>'
            % (html.escape(label), format(val, ','), c['unit'], html.escape(label),
               slot, pct, format(val, ','), c['unit'], html.escape(tag)))
    leg = ''
    if c['legend']:
        leg = '<div class="vz-leg">%s</div>' % ''.join(
            '<span><i class="s%d"></i>%s</span>' % (slot, html.escape(t))
            for t, slot in c['legend'])
    rows_tbl = ''.join('<tr><th>%s</th><td>%s%s</td></tr>'
                       % (html.escape(l), format(v, ','), c['unit']) for l, v, _, _ in c['rows'])
    return ('<figure class="vz" style="--lab:%s">' % c['lab'] + (
            '<figcaption><b>%s</b><span>%s</span></figcaption>'
            '%s<div class="vz-rows">%s</div>'
            '<details class="vz-tbl"><summary>값으로 보기</summary>'
            '<table><tbody>%s</tbody></table></details>'
            '<p class="vz-src">%s</p></figure>'
            % (html.escape(c['title']), html.escape(c['note']), leg,
               ''.join(bars), rows_tbl, html.escape(c['src']))))


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
    body = body.replace('<p>{{CHART1}}</p>', chart(CHART1)) \
               .replace('<p>{{CHART2}}</p>', chart(CHART2)) \
               .replace('<p>{{CHART3}}</p>', chart(CHART3))
    toc = ''.join('<li><a href="#d%ds%d">%s</a></li>' % (i, j, html.escape(t))
                  for j, t in enumerate(headings(d['md'])))
    nav = ''.join('<a href="%s"%s>%s</a>'
                  % (META[j]['file'], ' aria-current="page"' if j == i else '',
                     html.escape(META[j]['nav']))
                  for j in range(len(docs))
                  if META[i].get('internal') or not META[j].get('internal'))
    nxt = (i + 1) % len(docs)
    if META[nxt].get('internal'):
        nxt = (nxt + 1) % len(docs)
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
