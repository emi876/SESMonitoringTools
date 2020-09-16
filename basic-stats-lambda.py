import boto3
import json
from botocore.exceptions import ClientError
from datetime import date, timedelta
import os
from botocore.vendored import requests

AWS_REGION = "us-east-1"
client = boto3.client('ses', region_name=AWS_REGION)
webhook_url = os.environ['SLACK_WEBHOOK']


def async_send_slack_message(payload):

    data_to_send = json.dumps(payload)

    response = requests.post(
        webhook_url,
        data=data_to_send,
        headers=None
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error {}, the response is: {}. Payload: {}'.format(
                response.status_code, response.text, data_to_send)
        )
    raise ValueError(response.json())


def convert_to_singapore_sorted_range(utc_date_time_object_range):
    '''
    Function to sort the given date times and SGT. Technically since they are TZ aware, there are better
    ways to do this conversion to your timezone, i just prefer the explicitness of it.
    '''
    result = []
    sorted_utc_date_time_object_range = sorted(utc_date_time_object_range)
    for date_time_obj in sorted_utc_date_time_object_range:
        sgt_time = date_time_obj + timedelta(hours=8)

        sgt_time_str = sgt_time.strftime("%H:%M:%S on %d %B, %Y")
        result.append(sgt_time_str)

    return result


def get_overall_stats(response_dict):
    total_deliveries = 0
    total_bounce = 0
    total_complaint = 0
    total_reject = 0

    reject_timestamps = []
    bounce_timestamps = []
    complaint_timestamps = []

    verdict = "All good!"

    send_data_points = response_dict.get("SendDataPoints", [])

    for data_point in send_data_points:
        data_point_deliveries = data_point.get("DeliveryAttempts", 0)
        data_point_bounce = data_point.get("Bounces", 0)
        data_point_complaint = data_point.get("Complaints", 0)
        data_point_reject = data_point.get("Rejects", 0)
        data_point_timestamp = data_point.get("Timestamp")

        total_bounce += data_point_bounce
        total_reject += data_point_reject
        total_complaint += data_point_complaint

        total_deliveries += data_point_deliveries

        if data_point_bounce:
            bounce_timestamps.append(data_point_timestamp)
        if data_point_reject:
            reject_timestamps.append(data_point_timestamp)
        if data_point_complaint:
            complaint_timestamps.append(data_point_timestamp)

    bounce_list = convert_to_singapore_sorted_range(bounce_timestamps)
    reject_list = convert_to_singapore_sorted_range(reject_timestamps)
    complaint_list = convert_to_singapore_sorted_range(complaint_timestamps)

    if bounce_list or reject_list or complaint_list:
        verdict = "Warning - investigate!"
    else:
        verdict = "All good!"

    if total_deliveries == 0:
        return {
            "verdict": "Warning - Nothing sent!",
            "bounce_rate": 0,
            "complaint_rate": 0,
            "reject_rate": 0,
            "total_deliveries": 0,
            "problem_dates": {
                "reject_timestamps": bounce_list,
                "bounce_timestamps": reject_list,
                "complaint_timestamps": complaint_list
            }
        }
    return {
        "verdict": verdict,
        "bounce_rate": total_bounce / total_deliveries * 100,
        "complaint_rate": total_complaint / total_deliveries * 100,
        "reject_rate": total_reject / total_deliveries * 100,
        "total_deliveries": total_deliveries,
        "problem_dates": {
            "reject_timestamps": bounce_list,
            "bounce_timestamps": reject_list,
            "complaint_timestamps": complaint_list
        }
    }


def lambda_handler(event, context):

    try:
        response = client.get_send_statistics()
    except ClientError as e:
        return {
            'statusCode': 200,
            'body': json.dumps(str(e))
        }

    result_object = get_overall_stats(response)

    try:
        # date_now = datetime.strptime(date_str3, '%m-%d-%Y')
        today = date.today()
        d1 = today.strftime("%d/%m/%Y")
        result_heading = ':email: *SES STATS - {now_date}* \n *Verdict* : {verdict} \n *Reject Rate* : {reject_rate} \n\n {problem_dt}'.format(now_date = d1, verdict = result_object.get('verdict'), reject_rate = result_object.get('reject_rate'),problem_dt = result_object.get('problem_dates'))
        async_send_slack_message(payload={"text": result_heading})
        # async_send_slack_message(payload={"text":  json.dumps(result_object, indent=4, sort_keys=True, default=str)})
    except Exception as inst:
        result_object = {}
        result_object["slack_status"] = str(inst)
        return {
            'statusCode': 200,
            'body': json.dumps(result_object, indent=4, sort_keys=True, default=str)
        }
    return {
        'statusCode': 200,
        'body': json.dumps(result_object, indent=4, sort_keys=True, default=str)
    }
