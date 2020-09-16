from __future__ import print_function

import boto3
import json
import os
from botocore.vendored import requests

AWS_REGION = "us-east-1"
client = boto3.client('ses', region_name=AWS_REGION)
webhook = os.environ['SLACK_WEBHOOK']


def async_send_slack_message(payload):

    webhook_url = '{}'.format(webhook)
    data_to_send = json.dumps(payload)
    response = requests.post(
        webhook_url,
        data=data_to_send,
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error {}, the response is: {}. Payload: {}'.format(
                response.status_code, response.text, data_to_send)
        )


def get_content_from_message(message_content):
    notification_type = message_content["notificationType"]

    if notification_type == "Bounce":
        bounce_details = message_content["bounce"]
        bounce_type = bounce_details["bounceType"]
        bounce_sub_type = bounce_details["bounceSubType"]
        bounced_recipients_object = bounce_details["bouncedRecipients"]

        bounce_recipients_emails = ",".join([br["emailAddress"] for br in bounced_recipients_object])

        bounce_recipient_details = json.dumps(bounced_recipients_object)
        mail_details = json.dumps(
            message_content.get("mail", {}),
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )
        return "*NEW BOUNCE*\n\nType: {}\nSub type: {}\nRecipient emails: *{}*\nRecipient details: {}\nMessage content: {}\n".format(
            bounce_type,
            bounce_sub_type,
            bounce_recipients_emails,
            bounce_recipient_details,
            mail_details
        )
    elif notification_type == "Complaint":
        complaint_details = message_content["complaint"]
        complaint_type = message_content["complaintFeedbackType"]
        complaint_recipients_object = complaint_details["complainedRecipients"]
        complaint_timestamp = complaint_details["timestamp"]
        complaint_user_agent = complaint_details.get("userAgent", "")

        complaint_recipients_emails = ",".join([cr["emailAddress"] for cr in complaint_recipients_object])

        mail_details = json.dumps(
            message_content.get("mail", {}),
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )
        return "*NEW COMPLAINT!! *\n\nType: {}\nRecipient emails: *{}*\nTimestamp: {}\nUser agent: {}\nMessage content: {}\n".format(
            complaint_type,
            complaint_recipients_emails,
            complaint_timestamp,
            complaint_user_agent,
            mail_details
        )
    else:
        return "no idea! {} - {}".format(type(message_content), str(message_content))


def lambda_handler(event, context):
    for record in event['Records']:
        body = record["body"]

        body_message = json.loads(body)
        message_type = body_message.get('Type')
        message_content = "nothing in particular"
        if message_type == "Notification":

            message_content = get_content_from_message(json.loads(body_message["Message"]))
        async_send_slack_message(payload={"text": message_content})

    print("run finished")
