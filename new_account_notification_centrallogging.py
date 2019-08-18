import boto3, logging, os, json
from botocore.vendored import requests

log = logging.getLogger()
log.setLevel(logging.INFO)
SU = "SUCCESS"
FA = "FAILED"
s1 = os.environ['SNSmsgJ']
# sns_msg_jsn = json.loads('{"policyNames":[{"type":"kms","name":"secretsmanager","keyarn":"arn:aws:kms:us-east-1:278833423079:key/1a5fda48-6bda-4a56-9c60-22ccb0fb8348"},{"type":"s3","name":"ss-cf-templates"},{"type":"s3","name":"ss-cf-templates"},{"type":"s3","name":"ss-terraform-state"},{"type":"secrets","name":"artifactory-docker-user"}],"accountids":[]}')
topicArn = os.environ['SNStopicArn']
sns_msg_jsn = json.loads(os.environ['SNSmsgJ'])

def get_organization_info():

    try:
        orgc = boto3.client('organizations')

        accountList = orgc.list_accounts()
        for accountInfo in accountList["Accounts"]:
            accountId   = accountInfo['Id']
            accountName = accountInfo['Name']


    except Exception as e:
        log.error("ERROR: ")
        log.error("-- lambda_handler -- ERROR: {0}".format(str(e)))
        raise
    finally:
        log.info("-- lambda_handler -- Finished")


def lambda_handler(event, context):
    # sns_msg_jsn = json.dumps(s1)
    ssmc = boto3.client('ssm')
    orgc = boto3.client('organizations')
    cftc = boto3.client('cloudformation')
    accl = orgc.list_accounts()
    ssmp = FA
    accli = accl["Accounts"]
    sns_msg_jsn.update("accounts")
    for key in accli:
        accid = key["Id"]
        accountName = key["Name"]
        print(sns_msg_jsn)

        sns_msg_jsn["accountids"].append(accid)
        sns_msg_jsn["accounts"].update({"id":accid, "name":accountName})

        if ssmp == "FAILED":
            ssmp = "\"" + accid + "\""
        else:
            ssmp = "\"" + accid + "\"" + "," + ssmp
    print("New Json Object is: {0}".format(sns_msg_jsn))
    send_to_sns_topic(sns_msg_jsn)
    if ssmp != "FAILED":
        response = ssmc.put_parameter(Name="/org/member/centralloggings3/accounts", Value=ssmp, Type='String',
                                      Overwrite=True)
        try:
            stackupdate = cftc.update_stack_set(StackSetName=str(os.environ['StackSettoUpdate']),
                                                UsePreviousTemplate=True, Parameters=[
                    {
                        'ParameterKey': 'KINESISSHARDSN',
                        'UsePreviousValue': True
                    },
                    {
                        'ParameterKey': 'AccountsList',
                        'ParameterValue': ssmp,
                        'UsePreviousValue': False,
                    },
                    {
                        'ParameterKey': 'OrgID',
                        'UsePreviousValue': True
                    }
                ], Capabilities=[
                    'CAPABILITY_IAM'
                ])
        except Exception as e:
            log.error("template not found: " + str(e))
    responseDatain = {'Parameters': ssmp}
    if 'ResponseURL' in event:
        response = send(event, context, SU, responseDatain, None)
    else:
        response = responseDatain
    return {"Response": response}


def send_to_sns_topic(sns_msg_jsn):
    try:
        print("- send_to_sns_topic - SNS Message {0}".format(json.dumps(sns_msg_jsn, indent=4)))
        client = boto3.client('sns')
        response = client.publish(TopicArn=topicArn, Message=json.dumps(sns_msg_jsn), Subject='Organization Accounts')
        print("Send to SNS Arn {0}".format(response))
    except Exception as e:
        log.error("-- send_to_sns_topic -- ERROR: {0}".format(str(e)))


def send(event, context, responseStatus, responseData, physicalResourceId):
    responseUrl = event['ResponseURL']
    log.info("Event: " + str(event)
    log.info("ResponseURL: " + responseUrl)
    resB = {}
    resB['Status'] = responseStatus
    resB['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    resB['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    resB['StackId'] = event['StackId']
    resB['RequestId'] = event['RequestId']
    resB['LogicalResourceId'] = event['LogicalResourceId']
    resB['Data'] = responseData
    json_resB = json.dumps(resB)
    log.info("Response body: " + str(json_resB))
    headers = {'content-type': "", 'content-length': str(len(json_resB))}
    try:
        response = requests.put(responseUrl, data=json_resB, headers=headers)
        log.info("Status code: " + str(response.reason))
        return SU
    except Exception as e:
        log.error("send(..) failed executing requests.put(..): " + str(e))
        return SU
