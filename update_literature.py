import html, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG, HISTORY, DOCS = ROOT/'config/topics.json', ROOT/'data/literature.json', ROOT/'docs'

def get_json(url):
    req = Request(url, headers={'User-Agent':'joule-heating-literature-monitor/1.0'})
    with urlopen(req, timeout=30) as r: return json.loads(r.read().decode())

def norm(s): return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()
def esc(s): return html.escape(str(s or ''), quote=True)
def abstract(idx):
    if not idx: return ''
    pairs = [(pos, word) for word, positions in idx.items() for pos in positions]
    return ' '.join(word for _, word in sorted(pairs))
def openalex(query, year, limit):
    p={'search':query,'filter':f'from_publication_date:{year}-01-01,to_publication_date:{datetime.now(timezone.utc).date().isoformat()}','per-page':min(limit,100),'sort':'publication_date:desc'}
    rows=[]
    for w in get_json('https://api.openalex.org/works?'+urlencode(p)).get('results',[]):
        title=w.get('title') or ''
        if not title: continue
        doi=(w.get('doi') or '').replace('https://doi.org/','').lower()
        venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name','')
        rows.append({'title':title,'authors':', '.join((a.get('author') or {}).get('display_name','') for a in w.get('authorships',[])[:8]),'year':w.get('publication_year'),'venue':venue,'doi':doi,'url':w.get('doi') or w.get('id'),'abstract':abstract(w.get('abstract_inverted_index')),'source':'OpenAlex','type':w.get('type') or 'article','cited_by_count':w.get('cited_by_count')})
    return rows
def crossref(query, year, limit):
    p={'query.bibliographic':query,'filter':f'from-pub-date:{year}-01-01,until-pub-date:{datetime.now(timezone.utc).date().isoformat()}','rows':min(limit,100),'select':'DOI,title,author,published,container-title,type,URL'}
    rows=[]
    for x in get_json('https://api.crossref.org/works?'+urlencode(p)).get('message',{}).get('items',[]):
        title=(x.get('title') or [''])[0]
        if not title: continue
        d=x.get('published',{}).get('date-parts',[[None]])[0]
        doi=(x.get('DOI') or '').lower()
        rows.append({'title':title,'authors':', '.join(' '.join(filter(None,[a.get('given',''),a.get('family','')])) for a in x.get('author',[])[:8]),'year':d[0] if d else None,'venue':(x.get('container-title') or [''])[0],'doi':doi,'url':x.get('URL') or ('https://doi.org/'+doi),'abstract':'','source':'Crossref','type':x.get('type') or 'article','cited_by_count':None})
    return rows
def dedupe(rows):
    out={}
    for x in rows:
        key='doi:'+x['doi'] if x.get('doi') else 'title:'+norm(x.get('title'))
        if key not in out: out[key]=x
        else:
            if not out[key].get('abstract') and x.get('abstract'): out[key]['abstract']=x['abstract']
            if x.get('source') not in out[key].get('source',''): out[key]['source'] += ', '+x['source']
    return sorted(out.values(), key=lambda x:(x.get('year') or 0,x.get('title','')), reverse=True)
def page(payload):
    cards=[]
    for x in payload['items']:
        desc=x.get('abstract') or '暂无摘要，点击标题查看原始记录。'
        cards.append(f'<article><h2><a href="{esc(x.get("url") or "#")}" target="_blank" rel="noopener">{esc(x["title"])}</a></h2><p class="meta">{esc(x.get("authors"))} · {esc(x.get("year"))} · {esc(x.get("venue"))}</p><p class="tag">{esc(x.get("source"))} · {esc(x.get("type"))}</p><p>{esc(desc[:420])}</p><p class="meta">{esc(x.get("doi"))}</p></article>')
    tags=' '.join('<span>'+esc(c)+'</span>' for c in payload['concepts'])
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(payload['title'])+'</title><style>body{font-family:system-ui;max-width:1080px;margin:auto;padding:24px;background:#f6f8fb;color:#172033}header,article{background:white;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:14px 0;box-shadow:0 3px 12px #1720330b}h2{font-size:1.1rem}a{color:#155eef;text-decoration:none}.meta{color:#64748b;font-size:.9rem}.tag span,.tag{color:#155eef}.tag span{background:#e8f0ff;padding:4px 8px;border-radius:999px;margin:3px;font-size:.8rem}footer{color:#64748b;font-size:.85rem}</style></head><body><header><h1>'+esc(payload['title'])+'</h1><p>'+esc(payload['description'])+'</p><p><b>'+str(len(payload['items']))+'</b> 篇文献 · 更新于 '+esc(payload['updated_at'])+' · 来源：OpenAlex、Crossref</p><p class="tag">'+tags+'</p></header>'+''.join(cards)+'<footer>自动化文献发现页面，不代表对所有数据库的完整覆盖。请以 DOI、出版社页面或原始数据库记录为准。</footer></body></html>'
def main():
    cfg=json.loads(CONFIG.read_text(encoding='utf-8')); rows=[]
    for q in cfg['queries']:
        for fn in (openalex,crossref):
            try: rows += fn(q,cfg['from_year'],cfg['max_results_per_query'])
            except Exception as e: print(type(e).__name__, q, e)
        time.sleep(.4)
    old=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else []
    payload={'title':cfg['title'],'description':cfg['description'],'concepts':cfg['concepts'],'updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'items':dedupe(old+rows)}
    HISTORY.write_text(json.dumps(payload['items'],ensure_ascii=False,indent=2),encoding='utf-8'); DOCS.mkdir(exist_ok=True)
    (DOCS/'data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); (DOCS/'index.html').write_text(page(payload),encoding='utf-8')
    print('Saved',len(payload['items']),'unique records')
if __name__=='__main__': main()
