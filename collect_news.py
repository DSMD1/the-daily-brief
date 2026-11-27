import json, re, html, sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = [(c,'香港電台','https://rthk.hk/rthk/news/rss/'+f+'.xml') for c,f in [('香港','c_expressnews_clocal'),('中國','c_expressnews_greaterchina'),('國際','c_expressnews_cinternational'),('商業經濟','c_expressnews_cfinance')]]
FEEDS += [(c,'BBC','https://feeds.bbci.co.uk/news/'+f+'/rss.xml') for c,f in [('國際','world'),('商業經濟','business'),('科技 AI','technology')]]
for category,query,gl,hl,ceid in [('香港','香港 新聞','HK','zh-HK','HK:zh-Hant'),('台灣','台灣 新聞','TW','zh-TW','TW:zh-Hant'),('中國','中國 經濟 政策','HK','zh-HK','HK:zh-Hant'),('國際','world news','US','en-US','US:en'),('科技 AI','AI technology','US','en-US','US:en'),('熱門趨勢','熱門話題 社會 文化','HK','zh-HK','HK:zh-Hant')]:
    FEEDS.append((category,'Google News','https://news.google.com/rss/search?'+urlencode(dict(q=query+' when:2d',gl=gl,hl=hl,ceid=ceid))))

def clean(s):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s or '')).split())

def collect():
    now=datetime.now(timezone.utc); stories=[]; seen=set(); failures=0
    for category,source,url in FEEDS:
        count=0
        try:
            with urlopen(Request(url,headers={'User-Agent':'DailyBrief RSS reader/1.0'}),timeout=20) as response:
                root=ET.fromstring(response.read(3_000_000))
            for item in root.findall('.//item'):
                title=clean(item.findtext('title')); link=(item.findtext('link') or '').strip()
                try:
                    published=parsedate_to_datetime(item.findtext('pubDate'))
                    if published.tzinfo is None: published=published.replace(tzinfo=timezone.utc)
                except (ValueError,TypeError,OverflowError): continue
                if not now-timedelta(hours=36)<=published<=now+timedelta(hours=1): continue
                publisher=clean(item.findtext('source')) or source
                if source=='Google News' and title.endswith(' - '+publisher): title=title[:-len(publisher)-3]
                key=re.sub(r'\W+','',title.casefold())
                if not key or key in seen or not link.startswith(('https://','http://')): continue
                seen.add(key)
                stories.append(dict(category=category,source=publisher,title=title,url=link,published_at=published.isoformat(),summary='' if source=='Google News' else clean(item.findtext('description'))[:700]))
                count+=1
                if count>=30: break
            print(f'{category} / {source}: {count} articles')
        except Exception as exc:
            failures+=1; print(f'WARNING {category} / {source}: {exc}',file=sys.stderr)
    if not stories: raise SystemExit('No recent articles collected')
    stories.sort(key=lambda s:s['published_at'],reverse=True)
    Path('raw_news.json').write_text(json.dumps({'collected_at':now.isoformat(),'articles':stories},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Total: {len(stories)} articles; {failures} failed feeds')

if __name__=='__main__': collect()
