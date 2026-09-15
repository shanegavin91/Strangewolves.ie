"""Extract editable values without reserializing the approved page."""
import json, re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []
    def text(self):
        return ''.join(c if isinstance(c,str) else c.text() for c in self.children)
    def descendants(self):
        for c in self.children:
            if isinstance(c,Node):
                yield c
                yield from c.descendants()
class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.root=Node(); self.node=self.root
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs,self.node); self.node.children.append(n)
        if tag not in {'img','meta','link','input','br','hr','source','use','path','circle','rect'}: self.node=n
    def handle_startendtag(self,tag,attrs):
        self.node.children.append(Node(tag,attrs,self.node))
    def handle_endtag(self,tag):
        n=self.node
        while n.parent:
            if n.tag==tag: self.node=n.parent; return
            n=n.parent
    def handle_data(self,data): self.node.children.append(data)
def matches(n,s):
    nth=re.search(r':nth-of-type\((\d+)\)',s)
    if nth:
        siblings=[c for c in n.parent.children if isinstance(c,Node) and c.tag==n.tag]
        if siblings.index(n)+1!=int(nth[1]): return False
        s=s[:nth.start()]
    if s.startswith('#'): return n.attrs.get('id')==s[1:]
    if s.startswith('.'): return s[1:] in n.attrs.get('class','').split()
    return n.tag==s
def select(root,selector):
    nodes=[root]
    for part in selector.split():
        nodes=[n for p in nodes for n in p.descendants() if matches(n,part)]
    assert len(nodes)==1,(selector,len(nodes))
    return nodes[0]
def main():
    parser=Parser(); parser.feed((ROOT/'dist/index.html').read_text())
    fields=[]; values={}
    def add(key,group,label,selector,kind='text',limit=1600):
        n=select(parser.root,selector)
        value=n.attrs['src'] if kind=='image' else n.text().strip()
        fields.append(dict(id=key,group=group,label=label,selector=selector,kind=kind,max=limit))
        values[key]=value
        if kind=='image':
            fields.append(dict(id=key+'_alt',group=group,label=label+' — image description',selector=selector,kind='alt',max=200))
            values[key+'_alt']=n.attrs.get('alt',label)
    add('opening','Opening','Opening paragraph','.hero-deck')
    add('hero_photo','Opening','Main photograph','.hero-media img','image')
    add('course_title','Beginners','Course heading','#start-title',limit=100)
    add('course_photo','Beginners','Course poster','.course-poster img','image')
    add('course_link','Beginners','Opening course link','.hero-course-link',limit=100)
    add('experienced_intro','Classes','Who the regular classes suit','#class-panel-first p:nth-of-type(2)')
    add('experienced_rounds','Classes','What to expect','#class-panel-first p:nth-of-type(3)')
    for i,name in enumerate(['Vinny','Marcus','John'],1):
        add('coach_'+str(i)+'_name','Coaches',name+' — name',f'.coach-card:nth-of-type({i}) h3',limit=100)
        add('coach_'+str(i)+'_role','Coaches',name+' — role',f'.coach-card:nth-of-type({i}) .coach-role',limit=100)
        add('coach_'+str(i)+'_bio','Coaches',name+' — introduction',f'.coach-card:nth-of-type({i}) p:nth-of-type(2)')
    add('ethos_intro','Club ethos','Club introduction','.manifesto-copy .large-copy')
    add('ethos_training','Club ethos','How we train','.coaches-copy p:nth-of-type(1)')
    add('ethos_trust','Club ethos','Trust and training partners','.coaches-copy p:nth-of-type(2)')
    add('ethos_photo','Club ethos','Club photograph','.documentary-photo img','image')
    add('grading_intro','Club ethos','The Wolves system','.standard-heading p:nth-of-type(2)')
    for level in ['bronze','silver','gold']:
        add(level+'_description','Club ethos',level.title()+' Wolves description',f'.{level} p')
    add('podcast_intro','Podcast','Podcast introduction','.podcast-copy .large-copy')
    add('podcast_photo','Podcast','Podcast artwork','.podcast-art img','image')
    add('gallery_intro','Gallery','Gallery introduction','.pack-heading p:nth-of-type(2)')
    for i in range(1,9):
        add('gallery_'+str(i)+'_photo','Gallery',f'Photo {i}',f'.wall-photo:nth-of-type({i}) img','image')
        add('gallery_'+str(i)+'_caption','Gallery',f'Photo {i} caption',f'.wall-photo:nth-of-type({i}) span',limit=100)
    add('visit_intro','Contact','Before a first visit','.contact-copy p:nth-of-type(2)')
    assets=[{'src':'./assets/'+p.name,'label':p.stem.replace('-',' ').title()} for p in sorted((ROOT/'dist/assets').glob('*')) if p.suffix.lower() in ['.jpg','.webp','.png']]
    (ROOT/'dist/editor-schema.json').write_text(json.dumps({'fields':fields,'assets':assets},indent=2)+'\n')
    (ROOT/'backend/baseline-content.json').write_text(json.dumps({'revision':'approved-20260915','values':values,'savedAt':'2026-09-15T00:00:00Z'},indent=2)+'\n')
    print(f'Extracted {len(fields)} editable fields.')
if __name__=='__main__': main()
