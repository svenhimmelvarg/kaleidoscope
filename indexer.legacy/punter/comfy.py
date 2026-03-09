import requests
import json
from .data import *
from .data import _t


def prompt(r):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "http://127.0.0.1:8188/",
        "Content-Type": "application/json",
        "Comfy-User": "",
        "Origin": "http://127.0.0.1:8188",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "Cache-Control": "max-age=0",
    }

    data = {
        "client_id": "32e09cfb894c4bbb96871be154fca963",
        "prompt": r.prompt,
        "extra_data": {"extra_pnginfo": r.metadata._asdict()},
    }
    open("ding-request-example.json", "w").write(json.dumps(data, indent=2))
    response = requests.post(
        r.endpoint, headers=headers, data=json.dumps(data, allow_nan=True)
    )
    return response.json()


__QUEUE__ = []


def work_queue_add(_id, payload):
    global __QUEUE__
    __QUEUE__.append(_t(_id=_id, payload=payload, status="pending"))


def work_queue_update(_id, status):
    pass


def track(prompt_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "http://127.0.0.1:8188/",
        "Comfy-User": "",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=4",
        "Cache-Control": "max-age=0",
    }

    # Check queue
    queue_response = requests.get("http://127.0.0.1:8188/api/queue", headers=headers)

    queue_data = queue_response.json()

    # Check if prompt_id is in running or pending
    in_running = any(
        item[1] == prompt_id for item in queue_data.get("queue_running", [])
    )
    in_pending = any(
        item[1] == prompt_id for item in queue_data.get("queue_pending", [])
    )
    for v in queue_data["queue_running"]:
        print(v[0], v[1], prompt_id)
        if v[1] == prompt_id:
            in_running = True
            break
        else:
            in_running = False
    for v in queue_data["queue_pending"]:
        print(v[0], v[1], prompt_id)
        if v[1] == prompt_id:
            in_pending = True
            break
        else:
            in_pending = False

    print(in_running, in_pending)
    # If not in queue, check history
    if not in_running and not in_pending:
        history_response = requests.get(
            "http://127.0.0.1:8188/api/history?max_items=64", headers=headers
        )
        history_data = history_response.json()

        if prompt_id not in history_data:
            raise Exception(f"JOB - prompt id {prompt_id} does not exist")

        # Loop until prompt_id is in history (already there at this point)
        while True:
            if prompt_id in history_data:
                return {
                    prompt_id: {"outputs": history_data[prompt_id].get("outputs", {})}
                }

            # Re-check history
            history_response = requests.get(
                "http://127.0.0.1:8188/api/history?max_items=64", headers=headers
            )
            history_data = history_response.json()

    # If still in queue, keep checking until it's done
    print("Waiting for run to complete, prompt_id:", prompt_id)
    while in_running or in_pending:
        queue_response = requests.get(
            "http://127.0.0.1:8188/api/queue", headers=headers
        )
        queue_data = queue_response.json()
        in_running = False
        in_pending = False
        for v in queue_data["queue_running"]:
            print(v[0], v[1], prompt_id)
            if v[1] == prompt_id:
                in_running = True
                break
            else:
                in_running = False
        for v in queue_data["queue_pending"]:
            print(v[0], v[1], prompt_id)
            if v[1] == prompt_id:
                in_pending = True
                break
            else:
                in_pending = False

        if not in_running and not in_pending:
            # Check history once it's out of the queue
            history_response = requests.get(
                "http://127.0.0.1:8188/api/history?max_items=64", headers=headers
            )
            history_data = history_response.json()

            if prompt_id not in history_data:
                raise Exception(
                    f"JOB - prompt id {prompt_id} does not exist and was not in history_data: {history_data.keys()}"
                )

            return {prompt_id: {"outputs": history_data[prompt_id].get("outputs", {})}}
        # print("Sleep 1s", in_running, in_pending)
        import time

        time.sleep(1)


def cancel(prompt_id):
    """Cancel a ComfyUI task - handles both pending and running tasks"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "http://127.0.0.1:8188/",
        "Content-Type": "application/json",
        "Comfy-User": "",
        "Origin": "http://127.0.0.1:8188",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "Cache-Control": "max-age=0",
    }
    print("Cancelling:", prompt_id)

    queue_response = requests.get("http://127.0.0.1:8188/api/queue", headers=headers)
    queue_data = queue_response.json()

    in_running = any(
        item[1] == prompt_id for item in queue_data.get("queue_running", [])
    )

    if in_running:
        data = {"prompt_id": prompt_id}
        response = requests.post(
            "http://127.0.0.1:8188/api/interrupt",
            headers=headers,
            data=json.dumps(data),
        )
    else:
        data = {"delete": [prompt_id]}
        response = requests.post(
            "http://127.0.0.1:8188/api/queue", headers=headers, data=json.dumps(data)
        )

    print("Cancelling complete:", prompt_id)
    return response.json()
