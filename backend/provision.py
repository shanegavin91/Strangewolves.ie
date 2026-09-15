"""Provision the editor through AWS Core's call_boto3 adapter; no user invitations."""
import json

async def provision(call_boto3):
    region='eu-west-1'
    account=(await call_boto3(service_name='sts',operation_name='GetCallerIdentity'))['Account']
    if account!='544795558099': raise ValueError('Wrong AWS account')
    public='strangewolves-ie-site-544795558099'
    private='strangewolves-editor-544795558099'
    site='https://d2roxk7zsux5nf.cloudfront.net'
    buckets=await call_boto3(service_name='s3',operation_name='ListBuckets')
    if private not in [b['Name'] for b in buckets['Buckets']]:
        await call_boto3(service_name='s3',operation_name='CreateBucket',region_name=region,params={'Bucket':private,'CreateBucketConfiguration':{'LocationConstraint':region}})
    await call_boto3(service_name='s3',operation_name='PutPublicAccessBlock',region_name=region,params={'Bucket':private,'PublicAccessBlockConfiguration':{'BlockPublicAcls':True,'IgnorePublicAcls':True,'BlockPublicPolicy':True,'RestrictPublicBuckets':True}})
    await call_boto3(service_name='s3',operation_name='PutBucketVersioning',region_name=region,params={'Bucket':private,'VersioningConfiguration':{'Status':'Enabled'}})
    await call_boto3(service_name='s3',operation_name='PutBucketEncryption',region_name=region,params={'Bucket':private,'ServerSideEncryptionConfiguration':{'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]}})
    role_name='StrangeWolvesEditorLambda'
    roles=await call_boto3(service_name='iam',operation_name='ListRoles')
    role=next((r for r in roles['Roles'] if r['RoleName']==role_name),None)
    if not role:
        role=(await call_boto3(service_name='iam',operation_name='CreateRole',params={'RoleName':role_name,'AssumeRolePolicyDocument':json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]}),'Description':'Strange Wolves website content editor only'}))['Role']
    policy={'Version':'2012-10-17','Statement':[
      {'Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':[f'arn:aws:s3:::{private}/draft.json',f'arn:aws:s3:::{private}/history/*',f'arn:aws:s3:::{public}/content/site.json']},
      {'Effect':'Allow','Action':['s3:ListBucket'],'Resource':f'arn:aws:s3:::{private}','Condition':{'StringLike':{'s3:prefix':'history/*'}}},
      {'Effect':'Allow','Action':['s3:PutObject'],'Resource':f'arn:aws:s3:::{public}/uploads/*'},
      {'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{region}:{account}:log-group:/aws/lambda/strangewolves-editor:*'}]}
    await call_boto3(service_name='iam',operation_name='PutRolePolicy',params={'RoleName':role_name,'PolicyName':'ContentEditorStorage','PolicyDocument':json.dumps(policy)})
    logs=await call_boto3(service_name='logs',operation_name='DescribeLogGroups',region_name=region,params={'logGroupNamePrefix':'/aws/lambda/strangewolves-editor'})
    if not any(g['logGroupName']=='/aws/lambda/strangewolves-editor' for g in logs['logGroups']):
        await call_boto3(service_name='logs',operation_name='CreateLogGroup',region_name=region,params={'logGroupName':'/aws/lambda/strangewolves-editor'})
    await call_boto3(service_name='logs',operation_name='PutRetentionPolicy',region_name=region,params={'logGroupName':'/aws/lambda/strangewolves-editor','retentionInDays':30})
    pools=await call_boto3(service_name='cognito-idp',operation_name='ListUserPools',region_name=region,params={'MaxResults':60})
    pool=next((p for p in pools['UserPools'] if p['Name']=='strangewolves-editor'),None)
    if not pool:
        pool=(await call_boto3(service_name='cognito-idp',operation_name='CreateUserPool',region_name=region,params={'PoolName':'strangewolves-editor','AdminCreateUserConfig':{'AllowAdminCreateUserOnly':True},'AutoVerifiedAttributes':['email'],'UsernameAttributes':['email'],'UsernameConfiguration':{'CaseSensitive':False},'Policies':{'PasswordPolicy':{'MinimumLength':12,'RequireUppercase':True,'RequireLowercase':True,'RequireNumbers':True,'RequireSymbols':True,'TemporaryPasswordValidityDays':7}},'AccountRecoverySetting':{'RecoveryMechanisms':[{'Priority':1,'Name':'verified_email'}]}}))['UserPool']
    pool_id=pool['Id']
    groups=await call_boto3(service_name='cognito-idp',operation_name='ListGroups',region_name=region,params={'UserPoolId':pool_id})
    if not any(g['GroupName']=='editors' for g in groups['Groups']):
        await call_boto3(service_name='cognito-idp',operation_name='CreateGroup',region_name=region,params={'UserPoolId':pool_id,'GroupName':'editors','Description':'Club website editors; no public membership access'})
    clients=await call_boto3(service_name='cognito-idp',operation_name='ListUserPoolClients',region_name=region,params={'UserPoolId':pool_id,'MaxResults':60})
    client=next((c for c in clients['UserPoolClients'] if c['ClientName']=='club-editor'),None)
    if not client:
        client=(await call_boto3(service_name='cognito-idp',operation_name='CreateUserPoolClient',region_name=region,params={'UserPoolId':pool_id,'ClientName':'club-editor','GenerateSecret':False,'AllowedOAuthFlowsUserPoolClient':True,'AllowedOAuthFlows':['code'],'AllowedOAuthScopes':['openid','email','aws.cognito.signin.user.admin'],'CallbackURLs':[site+'/admin/index.html'],'LogoutURLs':[site+'/admin/index.html'],'SupportedIdentityProviders':['COGNITO'],'PreventUserExistenceErrors':'ENABLED','AccessTokenValidity':60,'IdTokenValidity':60,'RefreshTokenValidity':1,'TokenValidityUnits':{'AccessToken':'minutes','IdToken':'minutes','RefreshToken':'days'},'EnableTokenRevocation':True}))['UserPoolClient']
    domain='strangewolves-editor-'+account
    detail=await call_boto3(service_name='cognito-idp',operation_name='DescribeUserPoolDomain',region_name=region,params={'Domain':domain})
    if not detail.get('DomainDescription',{}).get('UserPoolId'):
        await call_boto3(service_name='cognito-idp',operation_name='CreateUserPoolDomain',region_name=region,params={'UserPoolId':pool_id,'Domain':domain})
    elif detail['DomainDescription']['UserPoolId']!=pool_id: raise ValueError('Sign-in domain belongs to another pool')
    apis=await call_boto3(service_name='apigatewayv2',operation_name='GetApis',region_name=region)
    api=next((a for a in apis.get('Items',[]) if a['Name']=='strangewolves-editor'),None)
    if not api:
        api=await call_boto3(service_name='apigatewayv2',operation_name='CreateApi',region_name=region,params={'Name':'strangewolves-editor','ProtocolType':'HTTP','CorsConfiguration':{'AllowOrigins':[site],'AllowMethods':['GET','POST','OPTIONS'],'AllowHeaders':['authorization','content-type'],'MaxAge':300}})
    return {'privateBucket':private,'publicBucket':public,'roleArn':role['Arn'],'poolId':pool_id,'clientId':client['ClientId'],'apiId':api['ApiId'],'api':api['ApiEndpoint'],'authDomain':f'https://{domain}.auth.{region}.amazoncognito.com','redirectUri':site+'/admin/index.html'}
