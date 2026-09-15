"""Security and persistence contracts, without AWS credentials or network calls."""
import copy, importlib.util, io, json, os, sys, tempfile, types, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class ClientError(Exception):
    def __init__(self,code): self.response={'Error':{'Code':code}}
class Missing(ClientError): pass
class Storage:
    exceptions=types.SimpleNamespace(NoSuchKey=Missing)
    def __init__(self): self.items={}; self.writes=0
    def get_object(self,Bucket,Key):
        if (Bucket,Key) not in self.items: raise Missing('NoSuchKey')
        body,etag=self.items[(Bucket,Key)]
        return {'Body':io.BytesIO(body),'ETag':etag}
    def put_object(self,**k):
        key=(k['Bucket'],k['Key']); existing=self.items.get(key)
        if k.get('IfNoneMatch')=='*' and existing: raise ClientError('PreconditionFailed')
        if k.get('IfMatch') and (not existing or existing[1]!=k['IfMatch']): raise ClientError('PreconditionFailed')
        self.writes+=1; etag='"'+str(self.writes)+'"'; self.items[key]=(k['Body'],etag); return {'ETag':etag}

class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); folder=Path(cls.tmp.name)
        (folder/'handler.py').write_bytes((ROOT/'backend/handler.py').read_bytes())
        (folder/'editor-schema.json').write_bytes((ROOT/'dist/editor-schema.json').read_bytes())
        sys.modules['boto3']=types.SimpleNamespace(client=lambda _:Storage())
        sys.modules['botocore.exceptions']=types.SimpleNamespace(ClientError=ClientError)
        os.environ.update(PRIVATE_BUCKET='private',PUBLIC_BUCKET='public')
        spec=importlib.util.spec_from_file_location('editor_handler',folder/'handler.py'); cls.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)
    def setUp(self):
        self.m=self.module; self.m.s3=Storage(); self.live=json.loads((ROOT/'backend/baseline-content.json').read_text())
        self.m.write('public','content/site.json',self.live)
    def call(self,path,body=None,groups='editors',token_use='access'):
        event={'rawPath':path,'requestContext':{'http':{'method':'POST' if body is not None else 'GET'},'authorizer':{'jwt':{'claims':{'sub':'test-editor','token_use':token_use,'cognito:groups':groups}}}},'body':json.dumps(body or {})}
        r=self.m.handler(event,None); return r['statusCode'],json.loads(r['body'])
    def test_non_editors_and_id_tokens_cannot_read_or_write(self):
        before=self.m.s3.writes
        for group,token in [('', 'access'),('not-editors','access'),('editors','id')]:
            self.assertEqual(self.call('/editor',groups=group,token_use=token)[0],403)
            self.assertEqual(self.call('/publish',{},groups=group,token_use=token)[0],403)
        self.assertEqual(before,self.m.s3.writes)
    def test_draft_does_not_publish_and_stale_write_is_rejected(self):
        _,state=self.call('/editor'); content={'values':copy.deepcopy(self.live['values'])};content['values']['opening']='A saved draft only.'
        self.assertEqual(self.call('/draft',{'content':content,'etag':state['etag']})[0],200)
        self.assertEqual(self.m.read('public','content/site.json')[0],self.live)
        self.assertEqual(self.call('/draft',{'content':content,'etag':state['etag']})[0],409)
    def test_publish_archives_old_content_and_does_not_expose_editor_id(self):
        _,state=self.call('/editor'); content={'values':copy.deepcopy(self.live['values'])};content['values']['opening']='Updated opening.'
        _,saved=self.call('/draft',{'content':content,'etag':state['etag']})
        self.assertEqual(self.call('/publish',{'etag':saved['etag'],'publishedEtag':'stale'})[0],409)
        status,published=self.call('/publish',{'etag':saved['etag'],'publishedEtag':state['publishedEtag']})
        self.assertEqual(status,200);self.assertNotIn('editor',published['published'])
        history=[json.loads(v[0]) for (b,k),v in self.m.s3.items.items() if k.startswith('history/')]
        self.assertEqual(history,[self.live])
    def test_unsafe_images_unknown_fields_and_html_upload_are_rejected(self):
        for source in ['javascript:alert(1)','https://example.com/photo.jpg','./uploads/../../admin/index.html']:
            content={'values':copy.deepcopy(self.live['values'])};content['values']['hero_photo']=source
            self.assertEqual(self.call('/draft',{'content':content,'etag':'missing'})[0],400)
        content={'values':copy.deepcopy(self.live['values'])};content['values']['extra']='x'
        self.assertEqual(self.call('/draft',{'content':content,'etag':'missing'})[0],400)
        import base64
        self.assertEqual(self.call('/images',{'base64':base64.b64encode(b'<svg onload="alert(1)"/>').decode()})[0],400)
if __name__=='__main__': unittest.main()
