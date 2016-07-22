#!/usr/bin/python

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from geopy.geocoders import GoogleV3
from s2sphere import *

import argparse
import logging
import json
import os
import random
import sys
import time


app = Flask(__name__)
log = logging.getLogger(__name__)
position = (0, 0)
targeted_cells = []
config = None


def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name)

    log.info('Your given location: %s', loc.address.encode('utf-8'))
    log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)
    
    return (loc.latitude, loc.longitude, loc.altitude)


def cell_to_latlng(data):
    cells = []
    for cid in data:
        cell = []
        for i in range(0,4):
            p = Cell(cid).get_vertex_raw(i)
            cell.append( (LatLng.latitude(p).degrees, LatLng.longitude(p).degrees) )
        cells.append(cell)
    return cells


@app.route("/grid/", methods=['POST'])
def grid():
    try:
        target = request.form.getlist("bounds")
    except:
        abort(500)

    if not target:
        abort(500)

    ne = LatLng.from_degrees(float(target[0]), float(target[1]))
    sw = LatLng.from_degrees(float(target[2]), float(target[3]))
    target_rect = LatLngRect.from_point_pair(ne, sw)

    coverer = RegionCoverer()
    coverer.min_level = 12
    coverer.max_level = 12
    covering = coverer.get_covering(target_rect)

    cells = cell_to_latlng(targeted_cells)

    return jsonify(cells)


@app.route("/target/", methods=['POST'])
def target():
    try:
        cell_lat = request.form.get("lat")
        cell_lng = request.form.get("lng")
    except:
        abort(500)

    if not cell_lat or not cell_lng:
        abort(500)

    cellid = CellId.from_lat_lng(LatLng.from_degrees(float(cell_lat), float(cell_lng))).parent(12)
    if cellid in targeted_cells:
        targeted_cells.remove( cellid )
    else:
        targeted_cells.append( cellid )

    cells = cell_to_latlng(targeted_cells)

    return jsonify( cells )


@app.route("/save/", methods=['POST'])
def save():
    target_path = os.path.abspath(config.file)
    cellids = []
    for c in targeted_cells:
        cellids.append(c.to_token())
    with open(target_path, 'w') as target_file:
        target_file.write(json.dumps(cellids))
    return jsonify( "%s cells were saved to %s"%(len(targeted_cells), target_path) )


@app.route("/load/", methods=['POST'])
def load():
    target_path = os.path.abspath(config.file)
    if not os.path.isfile(target_path):
        return jsonify( [], "Missing data file\n\nExpected location: %s"%(target_path) )
    with open(target_path, 'r') as target_file:
        cell_tokens = json.loads(target_file.read())
    global targeted_cells
    targeted_cells = []
    for t in cell_tokens:
        targeted_cells.append( CellId.from_token(t) )

    cells = cell_to_latlng(targeted_cells)

    return jsonify( cells, "%s cells were loaded from %s"%(len(targeted_cells), target_path) )


@app.route("/")
def index():
    return render_template("/index.html", center=position)


def main():
    # parse args
    parser = argparse.ArgumentParser(description = "Google S2 Mapping Test")
    parser.add_argument('-l', '--location', help="starting location", default='San Jose, CA')
    parser.add_argument('-a', '--address', help="address/host for server", default='localhost')
    parser.add_argument('-p', '--port', help="port for server", default='8888')
    parser.add_argument('-f', '--file', help="targets file location", default='targets.json')
    global config
    config = parser.parse_args()
    print type(config)

    # log settings
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)s] [%(levelname)s] %(message)s')

    # get start position
    global position
    position = get_pos_by_name(config.location)

    # create target.json
    target_path = os.path.abspath(config.file)
    if not os.path.isfile(target_path):
        with open(target_path, 'w') as target_file:
            target_file.write('[]')

    app.run(host=config.address, port=config.port)


if __name__ == '__main__':
    sys.exit(main())
