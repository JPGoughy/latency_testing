import os
import boto3
from requests import Session
from multiprocessing import Process, Queue
from datetime import datetime
import time

RUN_TIME = 120 ### NOTE - Time in seconds script is to run
TARGET = "0.0.0.0:5006"
START_TIME = time.time()
SESSION = Session()
SESSION.trust_env = False
CLOUDWATCH = boto3.client(
    "cloudwatch",
    region_name="eu-west-2",
    aws_access_key_id=os.environ["access_key"],
    aws_secret_access_key=os.environ["secret_key"],
)
CLOUDWATCH_LOGS = boto3.client(
    "logs",
    region_name="eu-west-2",
    aws_access_key_id=os.environ["access_key"],
    aws_secret_access_key=os.environ["secret_key"],
)

def call(q):
    pre_time = time.time()
    request = SESSION.get(f"http://{TARGET}/latency_test", verify=False)
    post_time = time.time()
    diff = post_time - pre_time
    q.put((request, diff, pre_time))

def upload(q, responses, stream_name):
    formatted_time = datetime.fromtimestamp(responses[2])
    CLOUDWATCH_LOGS.put_log_events(
        logGroupName="/wavelength/ping-data",
        logStreamName=stream_name,
        logEvents=[
            {"message": f"{str(responses[0].status_code)} - {str(responses[0].text)}", "timestamp": int(responses[2] * 1000)}
        ],
    )
    CLOUDWATCH.put_metric_data(
        Namespace="Wavelength",
        MetricData=[
            {
                "MetricName": "Round Trip Time",
                "Dimensions": [
                    {"Name": "target", "Value": TARGET},
                ],
                "Timestamp": formatted_time,
                "Value": float(responses[1]),
                "Unit": "Milliseconds",
                "StorageResolution": 1,
            }
        ],
    )
    print(responses[0].status_code)

if __name__ == "__main__":
    request_queue = Queue()
    upload_queue = Queue()
    stream_name = "HTTP_run_start_time_{time}".format(
        time=datetime.now().isoformat()
    ).replace(":", "_")
    CLOUDWATCH_LOGS.create_log_stream(
        logGroupName="/wavelength/ping-data", logStreamName=stream_name
    )
    print(datetime.now())
    total = 0
    while (time.time() - START_TIME) < RUN_TIME:
        rq = Process(target=call, args=(request_queue, ))
        rq.start()
        responses = request_queue.get()
        total += 1
        uq = Process(
            target=upload,
            args=(
                upload_queue,
                responses,
                stream_name,
            ),
        )
        uq.start()
    print(datetime.now())
    print(total)
    rq.join()
    uq.join()