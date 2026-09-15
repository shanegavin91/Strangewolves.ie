"""Private website editor API. Member records and payments are not enabled."""
import base64, json, logging, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
PRIVATE = os.environ['PRIVATE_BUCKET']
PUBLIC = os.environ['PUBLIC_BUCKET']
SCHEMA = json.loads(Path(__file__).with_name('editor-schema.json').read_text())
FIELDS = {f['id']: f for f in SCHEMA['fields']}
ASSETS = {a['src'] for a in SCHEMA['assets']}
LOG = logging.getLogger(__name__)

def response(status, data):
    return {'statusCode':status,'headers':{'Content-Type':'application/json','Cache-Control':'no-store'},'body':json.dumps(data)}
def read(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    with r['Body'] as body: data = json.loads(body.read())
    return data, r['ETag']
def write(bucket, key, data, etag=None):
    kwargs = {'Bucket':bucket,'Key':key,'Body':json.dumps(data).encode(),'ContentType':'application/json','CacheControl':'no-store'}
    if etag == 'missing': kwargs['IfNoneMatch'] = '*'
    elif etag: kwargs['IfMatch'] = etag
    return s3.put_object(**kwargs)['ETag']
def draft(published):
    try: return read(PRIVATE,'draft.json')
    except s3.exceptions.NoSuchKey: return published,'missing'
def validate(content):
    if not isinstance(content,dict) or set(content)!= {'values'}: raise ValueError('Invalid content format.')
    values=content['values']
    if not isinstance(values,dict) or set(values)!=set(FIELDS): raise ValueError('All website fields are required.')
    for key,value in values.items():
        f=FIELDS[key]
        if not isinstance(value,str) or not value.strip() or len(value)>f['max']: raise ValueError(f['label']+' is missing or too long.')
        if f['kind']=='image' and value not in ASSETS and not re.fullmatch(r'\./uploads/[a-f0-9-]{36}\.(webp|png|jpg)',value): raise ValueError('Choose a club photo or upload an image.')
    return {'values':values}
def stamp(content, editor):
    return {**content,'revision':str(uuid.uuid4()),'savedAt':datetime.now(timezone.utc).isoformat(),'editor':editor}
def handler(event, context):
    claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
    groups=re.findall(r'[A-Za-z0-9_-]+',str(claims.get('cognito:groups','')))
    if claims.get('token_use')!='access' or 'editors' not in groups: return response(403,{'error':'Editor access is required.'})
    method=event['requestContext']['http']['method']
    path=event.get('rawPath','').rstrip('/')
    editor=claims.get('sub','unknown')
    try:
        body=event.get('body') or '{}'
        if event.get('isBase64Encoded'): body=base64.b64decode(body).decode()
        if len(body)>4500000: return response(413,{'error':'Please use an image smaller than 3 MB.'})
        data=json.loads(body)
        if not isinstance(data,dict): raise ValueError('Invalid request.')
        if method=='GET' and path=='/editor':
            live,live_etag=read(PUBLIC,'content/site.json'); saved,etag=draft(live)
            return response(200,{'published':live,'publishedEtag':live_etag,'draft':saved,'etag':etag})
        if method=='POST' and path=='/draft':
            content=stamp(validate(data.get('content')),editor)
            etag=data.get('etag')
            if not isinstance(etag,str): raise ValueError('Reload the editor before saving.')
            new_etag=write(PRIVATE,'draft.json',content,etag)
            return response(200,{'draft':content,'etag':new_etag})
        if method=='POST' and path=='/publish':
            live,live_etag=read(PUBLIC,'content/site.json'); saved,etag=draft(live)
            if etag!=data.get('etag') or live_etag!=data.get('publishedEtag'): return response(409,{'error':'Another editor saved changes. Reload before publishing.'})
            content=stamp(validate({'values':saved['values']}),editor)
            content.pop('editor',None)
            history_key='history/'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid.uuid4())+'.json'
            write(PRIVATE,history_key,live,'missing')
            new_etag=write(PUBLIC,'content/site.json',content,live_etag)
            return response(200,{'published':content,'publishedEtag':new_etag})
        if method=='GET' and path=='/history':
            rows=[]
            for page in s3.get_paginator('list_objects_v2').paginate(Bucket=PRIVATE,Prefix='history/'):
                for item in page.get('Contents',[]):
                    rows.append({'id':item['Key'].split('/',1)[1],'savedAt':item['LastModified'].isoformat(),'baseline':item['Key']=='history/approved-baseline.json'})
            rows.sort(key=lambda x:x['savedAt'],reverse=True)
            return response(200,{'versions':rows[:100]})
        if method=='GET' and path.startswith('/history/'):
            key=path[len('/history/'):]
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.json',key): raise ValueError('Invalid version.')
            content,_=read(PRIVATE,'history/'+key)
            return response(200,{'content':content})
        if method=='POST' and path=='/images':
            raw=base64.b64decode(data.get('base64',''),validate=True)
            if not 1<=len(raw)<=3*1024*1024: raise ValueError('Image must be smaller than 3 MB.')
            if raw[:3]==b'\xff\xd8\xff': ext,mime='jpg','image/jpeg'
            elif raw[:8]==b'\x89PNG\r\n\x1a\n': ext,mime='png','image/png'
            elif raw[:4]==b'RIFF' and raw[8:12]==b'WEBP': ext,mime='webp','image/webp'
            else: raise ValueError('Upload a JPG, PNG or WebP image.')
            key='uploads/'+str(uuid.uuid4())+'.'+ext
            s3.put_object(Bucket=PUBLIC,Key=key,Body=raw,ContentType=mime,CacheControl='public, max-age=31536000, immutable',IfNoneMatch='*')
            return response(201,{'src':'./'+key})
        return response(404,{'error':'Not found.'})
    except (ValueError,TypeError,KeyError):
        return response(400,{'error':'Please check the fields and image format, then try again.'})
    except ClientError as exc:
        code=exc.response['Error']['Code']
        if code in ['PreconditionFailed','ConditionalRequestConflict']: return response(409,{'error':'This draft changed in another session. Reload before saving.'})
        if code=='NoSuchKey': return response(404,{'error':'That saved version was not found.'})
        LOG.exception('Editor storage request failed')
        return response(503,{'error':'The change could not be completed. Please retry.'})
