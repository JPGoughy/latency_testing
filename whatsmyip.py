import os
import time
import boto3
import requests
from pathlib import Path

whom = os.getenv("WL_ICMP_WHOM", "xxxx")
stream_name = f"PublicIP_{whom}"
created = True
cloudwatch = boto3.client(
    "logs",
    region_name="eu-west-2",
    aws_access_key_id=os.environ["access_key"],
    aws_secret_access_key=os.environ["secret_key"],
)
if not os.path.exists("/tmp/ip-logger-ran.tmp"):
    streams = cloudwatch.describe_log_streams(
        logGroupName=f"/wavelength/ping-data/{whom}",
        logStreamNamePrefix=stream_name,
        limit=1,
    )
    if not streams["logStreams"]:
        cloudwatch.create_log_stream(
            logGroupName=f"/wavelength/ping-data/{whom}", logStreamName=stream_name
        )
        Path("/tmp/ip-logger-ran.tmp").touch()
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
