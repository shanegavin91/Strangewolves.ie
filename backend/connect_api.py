"""Connect the already-provisioned authenticated HTTP API to the packaged Lambda."""
async def connect(call_boto3, resources):
    r=resources; region='eu-west-1'; name='strangewolves-editor'
    functions=await call_boto3(service_name='lambda',operation_name='ListFunctions',region_name=region)
    existing=next((f for f in functions['Functions'] if f['FunctionName']==name),None)
    if existing:
        function=await call_boto3(service_name='lambda',operation_name='UpdateFunctionCode',region_name=region,params={'FunctionName':name,'S3Bucket':r['privateBucket'],'S3Key':'build/editor-api.zip'})
    else:
        function=await call_boto3(service_name='lambda',operation_name='CreateFunction',region_name=region,params={'FunctionName':name,'Runtime':'python3.12','Role':r['roleArn'],'Handler':'handler.handler','Code':{'S3Bucket':r['privateBucket'],'S3Key':'build/editor-api.zip'},'Timeout':15,'MemorySize':256,'Architectures':['arm64'],'Environment':{'Variables':{'PRIVATE_BUCKET':r['privateBucket'],'PUBLIC_BUCKET':r['publicBucket']}}})
    api_id=r['apiId']; function_arn=function['FunctionArn']
    integrations=await call_boto3(service_name='apigatewayv2',operation_name='GetIntegrations',region_name=region,params={'ApiId':api_id})
    integration=next((i for i in integrations.get('Items',[]) if i.get('IntegrationUri')==function_arn),None)
    if not integration:
        integration=await call_boto3(service_name='apigatewayv2',operation_name='CreateIntegration',region_name=region,params={'ApiId':api_id,'IntegrationType':'AWS_PROXY','IntegrationUri':function_arn,'PayloadFormatVersion':'2.0','TimeoutInMillis':15000})
    authorizers=await call_boto3(service_name='apigatewayv2',operation_name='GetAuthorizers',region_name=region,params={'ApiId':api_id})
    authorizer=next((a for a in authorizers.get('Items',[]) if a['Name']=='club-editors'),None)
    if not authorizer:
        authorizer=await call_boto3(service_name='apigatewayv2',operation_name='CreateAuthorizer',region_name=region,params={'ApiId':api_id,'Name':'club-editors','AuthorizerType':'JWT','IdentitySource':['$request.header.Authorization'],'JwtConfiguration':{'Audience':[r['clientId']],'Issuer':f'https://cognito-idp.{region}.amazonaws.com/'+r['poolId']}})
    routes=await call_boto3(service_name='apigatewayv2',operation_name='GetRoutes',region_name=region,params={'ApiId':api_id})
    for key in ['GET /editor','POST /draft','POST /publish','GET /history','GET /history/{id}','POST /images']:
        if not any(route['RouteKey']==key for route in routes.get('Items',[])):
            await call_boto3(service_name='apigatewayv2',operation_name='CreateRoute',region_name=region,params={'ApiId':api_id,'RouteKey':key,'Target':'integrations/'+integration['IntegrationId'],'AuthorizationType':'JWT','AuthorizerId':authorizer['AuthorizerId'],'AuthorizationScopes':['aws.cognito.signin.user.admin']})
    if not existing:
        await call_boto3(service_name='lambda',operation_name='AddPermission',region_name=region,params={'FunctionName':name,'StatementId':'EditorHttpApi','Action':'lambda:InvokeFunction','Principal':'apigateway.amazonaws.com','SourceArn':f'arn:aws:execute-api:{region}:544795558099:{api_id}/*/*','SourceAccount':'544795558099'})
    stages=await call_boto3(service_name='apigatewayv2',operation_name='GetStages',region_name=region,params={'ApiId':api_id})
    if not any(s['StageName']=='$default' for s in stages.get('Items',[])):
        await call_boto3(service_name='apigatewayv2',operation_name='CreateStage',region_name=region,params={'ApiId':api_id,'StageName':'$default','AutoDeploy':True,'DefaultRouteSettings':{'ThrottlingBurstLimit':10,'ThrottlingRateLimit':5}})
    return {'functionArn':function_arn,'authorizerId':authorizer['AuthorizerId'],'api':r['api']}
