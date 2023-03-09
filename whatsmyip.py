import os
import time
import boto3
import requests

whom = "BF_Mac_Test"
stream_name = f"PublicIP_{whom}"
created = True
cloudwatch = boto3.client(
    "logs",
    region_name="eu-west-2",
    aws_access_key_id=os.environ["access_key"],
    aws_secret_access_key=os.environ["secret_key"],
)
if not created:
    cloudwatch.create_log_stream(
        logGroupName=f"/wavelength/ping-data/{whom}", logStreamName=stream_name
    )
while True:
    pub_ip = requests.get("https://checkip.amazonaws.com/").text.strip()
    cloudwatch.put_log_events(
        logGroupName=f"/wavelength/ping-data/{whom}",
        logStreamName=stream_name,
        logEvents=[
            {
                "message": pub_ip,
                "timestamp": int(time.time() * 1000),
            }
        ],
    )
