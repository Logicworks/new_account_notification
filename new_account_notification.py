import boto3, logging, os, json
from botocore.vendored import requests

log = logging.getLogger()
log.setLevel(logging.INFO)

topicArn = os.environ['SNStopicArn']
sns_msg_jsn = json.loads(os.environ['SNSMessageTemplate'])

def lambda_handler(event, context):
    orgc = boto3.client('organizations')
    accl = orgc.list_accounts()
    accli = accl["Accounts"]
    #sns_msg_jsn.update("accounts")
    for key in accli:
        accid = key["Id"]
        accountName = key["Name"]
        print(sns_msg_jsn)

        sns_msg_jsn["accountids"].append(accid)
        #sns_msg_jsn["accounts"].update({"id":accid, "name":accountName})


    log.debug("New Json Object is: {0}".format(sns_msg_jsn))
    response = send_to_sns_topic(sns_msg_jsn)

    return {"Response": response}


def send_to_sns_topic(sns_msg_jsn):
    try:
        log.debug("- send_to_sns_topic - SNS Message {0}".format(json.dumps(sns_msg_jsn, indent=4)))
        client = boto3.client('sns')
        response = client.publish(TopicArn=topicArn, Message=json.dumps(sns_msg_jsn), Subject='Organization Accounts')
        log.debug("Send to SNS Arn {0}".format(response))
    except Exception as e:
        log.error("-- send_to_sns_topic -- ERROR: {0}".format(str(e)))



