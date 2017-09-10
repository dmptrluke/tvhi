from flask import Flask, Response, render_template, jsonify
from time import time

import flask
import requests
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


ME = config.get('tvhi', 'tvhi_url').rstrip('/')
DEVICE_ID = config.get('tvhi', 'device_id', fallback='tvhituner2')

TVH_URL = config.get('tvh', 'tvh_url').rstrip('/')
STREAM_URL = TVH_URL + "/stream/channel/{}?profile={}&weight={}"

# specifiy a stream profile that you want to use for adhoc transcoding in tvh, e.g. mp4
STREAM_PROFILE = config.get('tvh', 'stream_profile', fallback='pass')
STREAM_WEIGHT = config.getint('tvh', 'stream_weight', fallback=300)
TUNER_COUNT = config.getint('tvh', 'tuner_count', fallback=2)
TUNER_TYPE = config.get('tvh', 'tuner_type', fallback='Cable').title()


app = Flask(__name__)

tag = requests.get(TVH_URL + '/api/channeltag/list')
tag.raise_for_status()

hd_tag = ""
for entry in tag.json()['entries']:
    if entry['val'] == "HDTV":
        hd_tag = entry['key']


def truncate(content, length=150, suffix='...'):
    """
    Truncates a string after a certain number of characters.
    Function always tries to truncate on a word boundary.
    :rtype str
    """
    if not content:
        return None

    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix


########
# WEB UI
########

@app.route("/")
def listing():
    request = requests.get(TVH_URL + '/api/epg/events/grid?limit=100')
    request.raise_for_status()

    json = request.json()
    channels = {}

    for entry in json['entries']:
        if entry['channelUuid'] in channels:
            continue

        channels[entry['channelUuid']] = {
            "name": entry['channelName'],
            "icon": TVH_URL + entry['channelIcon'] + '.png',
            "uuid": entry['channelUuid'],
            "title": entry['title'],
            "description": truncate(entry.get('subtitle') or entry.get('summary'))
        }

    channels = channels.values()
    channels = sorted(channels, key=lambda c: c['name'])

    return render_template('listing.html', channels=channels)


@app.route('/watch/<uuid>/')
def watch(uuid):
    request = requests.get(TVH_URL + '/api/idnode/load?uuid=' + uuid)
    request.raise_for_status()

    json = request.json()
    entry = json['entries'][0]

    title = entry['text']

    url = STREAM_URL.format(entry['uuid'], 'mkv', STREAM_WEIGHT)
    return render_template('watch.html', title=title, url=url)


#####
# API
#####

@app.route('/discover.json')
def api_discover():
    return jsonify({
        'FriendlyName': 'HDHomeRun CONNECT',
        'ModelNumber': 'HDHR4-2DT',
        'FirmwareName': 'hdhomerun4_dvbt',
        'TunerCount': TUNER_COUNT,
        'DeviceID': DEVICE_ID,
        'FirmwareVersion': '20170815',
        'DeviceAuth': 'foobar80',
        'BaseURL': ME,
        'LineupURL': ME + '/lineup.json'
    })


@app.route('/lineup_status.json')
def api_status():
    return jsonify({
        'ScanInProgress': 0,
        'ScanPossible': 1,
        'Source': TUNER_TYPE,
        'SourceList': [TUNER_TYPE]
    })


@app.route('/lineup.json')
def api_lineup():
    grid = requests.get(TVH_URL + '/api/channel/grid')
    grid.raise_for_status()

    lineup = []
    for entry in grid.json()['entries']:
        lineup.append({
            "GuideNumber": str(entry['number']),
            "GuideName": entry['name'],
            "URL": STREAM_URL.format(entry['uuid'], STREAM_PROFILE, STREAM_WEIGHT),
            "HD": 1 if hd_tag in entry['tags'] else 0
        })

    return jsonify(lineup)


@app.route('/lineup.post', methods=['POST'])
def api_post():
    return ""

app.run(port=5004, host='0.0.0.0')