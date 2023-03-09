from subprocess import check_output, CalledProcessError
from multiprocessing import Process, Queue, Pool
import re
import os
import time
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

RUN_TIME = 121000000  ### NOTE - Time in seconds script is to run
START_TIME = time.time()
WHOM = "xxxx"  # This is the indentifier of which compute is running this
TARGET = "xxxx"
NUMBER_OF_PINGS = 50
### MAC REGEX

# REGEX = re.compile(
#     "(\d+) packets transmitted, (\d+) packets received, (\d+(?:.\d+)*)% packet loss\nround-trip min\/avg\/max\/stddev = (\d+.\d+)\/(\d+.\d+)\/(\d+.\d+)\/(\d+.\d+) ms"
# )

### Viking2
REGEX = re.compile(
    "(\d+) packets transmitted, (\d+) received, (\d+(?:.\d+)*)% packet loss, time \d+ms\nrtt min\/avg\/max\/mdev = (\d+.\d+)\/(\d+.\d+)\/(\d+.\d+)\/(\d+.\d+) ms"
)
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
STREAM_NAME = "ICMP_run_start_time_{time}".format(
    time=datetime.now().isoformat()
).replace(":", "_")


def ping():
    try:
        start_time = time.time()
        output = check_output(
            "ping -f -c {qty} {address}".format(address=TARGET, qty=NUMBER_OF_PINGS),
            shell=True,
        ).decode("utf-8")
        return (output, start_time, False)
    # q.put((output, start_time, False))
    except CalledProcessError as ping_error:
        print(
            f"""
        There was an error while trying to ping WL Zone.
        Error: {ping_error.output}
        Command: {ping_error.cmd}
        Code: {ping_error.returncode}
        """
        )
        return (ping_error, start_time, True)
        # q.put((ping_error, start_time, True))
    except Exception as unknown_error:
        print(f"Unknown Exception. {unknown_error}")
        return (unknown_error, start_time, True)
        # q.put((unknown_error, start_time, True))


def upload(ping_result):
    try:
        formatted_time = datetime.fromtimestamp(ping_result[1])
        has_errored = ping_result[2]
        if has_errored:
            if isinstance(ping_result[0], CalledProcessError):
                message = f"CalledProcessError {ping_result[0].output} - {ping_result[0].cmd} - {ping_result[0].returncode}"
            else:
                message = str(ping_result[0])
            CLOUDWATCH_LOGS.put_log_events(
                logGroupName=f"/wavelength/ping-data/{WHOM}",
                logStreamName=STREAM_NAME,
                logEvents=[
                    {
                        "message": message,
                        "timestamp": int(ping_result[1] * 1000),
                    }
                ],
            )
            CLOUDWATCH.put_metric_data(
                Namespace="Wavelength",
                MetricData=[
                    {
                        "MetricName": "Software Errors",
                        "Dimensions": [
                            {"Name": "target", "Value": TARGET},
                            {"Name": "source", "Value": WHOM},
                        ],
                        "Timestamp": formatted_time,
                        "Value": 1,
                        "Unit": "Count",
                        "StorageResolution": 1,
                    }
                ],
            )
        else:
            matches = re.findall(REGEX, ping_result[0])
            try:
                CLOUDWATCH_LOGS.put_log_events(
                    logGroupName=f"/wavelength/ping-data/{WHOM}",
                    logStreamName=STREAM_NAME,
                    logEvents=[
                        {
                            "message": str(ping_result[0]),
                            "timestamp": int(ping_result[1] * 1000),
                        }
                    ],
                )
            except ClientError as aws_error:
                print(f"Cannot upload Log Event to AWS. Error {aws_error}")
            try:
                CLOUDWATCH.put_metric_data(
                    Namespace="Wavelength",
                    MetricData=[
                        {
                            "MetricName": "Average Round Trip Time",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][4]),
                            "Unit": "Milliseconds",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Minimum Round Trip Time",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][3]),
                            "Unit": "Milliseconds",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Maximum Round Trip Time",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][5]),
                            "Unit": "Milliseconds",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Standard Deviation Round Trip Time",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][6]),
                            "Unit": "Milliseconds",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Packets Transmitted",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][0]),
                            "Unit": "Count",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Packets Received",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][1]),
                            "Unit": "Count",
                            "StorageResolution": 1,
                        },
                        {
                            "MetricName": "Packet Loss",
                            "Dimensions": [
                                {"Name": "target", "Value": TARGET},
                                {"Name": "source", "Value": WHOM},
                            ],
                            "Timestamp": formatted_time,
                            "Value": float(matches[0][2]),
                            "Unit": "Percent",
                            "StorageResolution": 1,
                        },
                    ],
                )
            except ClientError as aws_error:
                print(f"Cannot upload Event Data to AWS. Error {aws_error}")
    except Exception as uncaught_exception:
        print(f"Uncaught Exception: {uncaught_exception}")


if __name__ == "__main__":
    try:
        print("Hello! - Starting wavelength ICMP Latency Test")
        CLOUDWATCH_LOGS.create_log_stream(
            logGroupName=f"/wavelength/ping-data/{WHOM}", logStreamName=STREAM_NAME
        )
        with Pool(maxtasksperchild=10) as p:
            while True:
                p.apply_async(
                    ping,
                    callback=upload,
                    error_callback=lambda error: print("Async Error:", error),
                )
    except Exception as error:
        print(f"Something went wrong in the main thread. Error: {error}")
    finally:
        print("Goodbye! - Stopping wavelength ICMP Latency Test")
