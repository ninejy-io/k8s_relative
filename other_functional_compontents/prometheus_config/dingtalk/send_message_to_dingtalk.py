# coding: utf-8
## send message to dingtalk
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

url = "https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxxxxxx"


def call_dingtalk(data):
    headers = {"Content-Type": "application/json"}
    _data = {
        "msgtype": "text",
        "text": {
            "content": data
        },
        "at": {
            "atMobiles": [],
            "isAtAll": False
        }
    }

    try:
        r = requests.post(url, json=_data, headers=headers)
        res = r.json()
        if res['errcode'] == 0:
            print(data, '\nSend success.')
    except Exception as e:
        print(e)


@app.route('/dingtalk/alert', methods=['POST'])
def alert():
    _data = json.loads(request.data)
    alerts = _data.get('alerts')
    if alerts:
        for alt in alerts:
            labels = alt['labels']
            alert_name = labels['alertname']
            host_ip = labels['instance']
            alert_value = alt['annotations']['value']
            alert_time = alt['startsAt'].split('.')[0].replace('T', ' ')

            if alert_name == "HostOutOfDiskSpace":
                mp = labels['mountpoint']
                data = '''{}\n硬盘空闲率: {:.2f}%\n挂载点: {}\n主机信息: {}\n时间: {}'''.format(
                    alert_name,
                    float(alert_value),
                    labels['mountpoint'],
                    host_ip,
                    alert_time)
            else:
                data = '''{0}\n告警值: {1}\n主机信息: {2}\n时间: {3}'''.format(
                    alert_name,
                    alert_value,
                    host_ip,
                    alert_time)

            call_dingtalk(data)

    return jsonify({"code": "0", "msg": "success"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)
