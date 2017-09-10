from flask import Flask, Response, redirect
from time import time

import flask
import requests

ME = "http://localhost"

TVH_URL = "http://tracker.local:9981/{}"
STREAM_URL = TVH_URL.format("stream/channel/{}?profile={}")

app = Flask(__name__)

@app.route('/auto/<channel>')
def api_stream(channel):
    app.logger.info("Received stream request: {}".format(flask.request.url))
    url = ''
    channel = channel.replace('v', '')
    duration = flask.request.args.get('duration', default=0, type=int)

    if not duration == 0:
        duration += time()

    request = requests.get(TVH_URL.format('api/channel/grid'))
    request.raise_for_status()

    json = request.json()

    for entry in json['entries']:
        if str(entry['number']) == channel:
            url = STREAM_URL.format(entry['uuid'], 'pass')

    if not url:
        flask.abort(404)
    else:
        req = requests.get(url, stream=True)

        def generate():
            yield b''
            for chunk in req.iter_content(chunk_size=1024*1024):
                if not duration == 0 and not time() < duration:
                    req.close()
                    break
                yield chunk

        return Response(generate(), content_type=req.headers['content-type'], direct_passthrough=True)

app.run(port=5004, threaded=True)