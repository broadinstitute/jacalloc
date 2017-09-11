from flask import Flask, request, jsonify
import json
import sys
import random
from sqlalchemy import exc

from models import db, Resource

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

## Resources Table methods ##

def check_request(request_dict, keys):
    missing = []
    for k in keys:
        if k not in request_dict:
            missing.append(k)
    return missing

def create_resource(body):
    resource = Resource(
        name=body['name'],
        ip=body['ip'],
        in_use=body['in_use'],
        project=body['project']
    )
    db.session.add(resource)
    db.session.commit()

def update_resource(name, body):
    r = Resource.query.filter_by(name=name).first()
    if 'in_use' in body:
        r.in_use = body['in_use']
    if 'name' in body:
        r.name = body['name']
    if 'ip' in body:
        r.ip = body['ip']
    if 'project' in body:
        r.project = body['project']
    db.session.commit()

def delete_resource(name):
    Resource.query.filter(Resource.name == name).delete()
    db.session.commit()


def get_resource_by_name(name):
    return Resource.query.filter(Resource.name == name)[0].map()

def get_all_resources(in_use=None, project=None):
    if in_use and project:
        return [x.map() for x in Resource.query.filter(Resource.project == project).filter(Resource.in_use == in_use)]
    if project:
        return [x.map() for x in Resource.query.filter(Resource.project == project)]
    if in_use:
        return [x.map() for x in Resource.query.filter(Resource.in_use == in_use)]
    return [x.map() for x in Resource.query.all()]


def pick_random_resource(resources):
    x = random.randint(0, len(resources) - 1)
    return resources[x]

## Routes ##

@app.route('/')
def api_health():
    # TODO: check if can ping db
    return 'Service running!', 200


@app.route('/resources', methods=['GET', 'POST'])
def api_create_resource():
    errors = []
    print request

    if request.method == 'GET':
        resp = get_all_resources(in_use=request.args.get('in_use'), project=request.args.get('project'))
        return json.dumps(resp), 200

    elif request.method == 'POST':
        body = request.get_json()
        if not body:
            return "Empty request body", 400
        missing = check_request(body, ['name', 'ip', 'in_use', 'project'])

        # validate request
        if missing:
            return 'Request missing following fields: {}'.format(missing), 400
        else:
            # new resource
            if not Resource.query.filter_by(name=body['name']).first():
                try:
                    create_resource(body)
                    print "Created record for {0}".format(body['name'])
                    return json.dumps(body), 200
                except:
                    e = sys.exc_info()[0]
                    errors.append("Unable to create new record for {0}: {1}".format(body['name'], e))

            else:
                return "Resource already exists!", 409
        if errors:
            return str(errors), 500


@app.route('/resources/<name>', methods=['GET'])
def api_get_resource(name):
    resp = Resource.query.filter(Resource.name == name).first()
    if resp:
        return json.dumps(resp.map()), 200

    else:
        return "Resource not found!", 404


@app.route('/resources/name/<keyword>', methods=['GET'])
def api_get_by_search(keyword):
    try:
        resp = Resource.query.filter(Resource.name.op("~")(keyword))
        if resp:
            return json.dumps([x.map() for x in resp.all()]), 200
        else:
            return "No resources found matching regex!", 404

    except exc.DataError as e:
        return ("Invalid keyword \"{0}\". Try removing bad characters.".format(keyword, e)), 400


@app.route('/resources/<name>', methods=['POST'])
def api_update_resource(name):
    errors = []
    print request
    try:
        request.get_json()
    except:
        return "Empty request body", 400

    resp = Resource.query.filter(Resource.name == name).first()
    if resp:
        body = request.get_json()
        try:
            update_resource(name, body)
            new = get_resource_by_name(name)
            return json.dumps(new), 200
        except:
            e = sys.exc_info()[0]
            errors.append("Unable to update record for {0}: {1}".format(body['name'], e))

    else:
        return "Resource not found. Cannot update.", 404

    if errors:
        return str(errors), 500


@app.route('/resources/<name>', methods=['DELETE'])
def api_delete_resource(name):
    try:
        delete_resource(name)
        return "Deleted resource {0}".format(name), 201
    except:
        e = sys.exc_info()[0]
        return str(e), 500


@app.route('/resources/allocate', methods=['POST'])
def api_allocate():
    # choose random free resource, and allocate

    free = get_all_resources(in_use="false", project=request.args.get('project'))
    if free:
        try:
            allocated = pick_random_resource(free)
            update_resource(allocated['name'], {'in_use': True})
            allocated['in_use'] = True
            return json.dumps(allocated), 200
        except:
            e = sys.exec_info()[0]
            return str(e), 500
    else:
        return "No resources are free!", 412



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')