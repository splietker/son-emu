from flask_restful import Resource
from flask import Response, request
from emuvim.api.openstack.openstack_dummies.base_openstack_dummy import BaseOpenstackDummy
import logging
import json


LOG = logging.getLogger("api.openstack.glance")


class GlanceDummyApi(BaseOpenstackDummy):
    def __init__(self, in_ip, in_port, compute):
        super(GlanceDummyApi, self).__init__(in_ip, in_port)
        self.compute = compute
        self.api.add_resource(Shutdown,
                              "/shutdown")
        self.api.add_resource(GlanceListApiVersions,
                              "/versions")
        self.api.add_resource(GlanceSchema,
                              "/v2/schemas/image",
                              "/v2/schemas/metadefs/namespace",
                              "/v2/schemas/metadefs/resource_type")
        self.api.add_resource(GlanceListImagesApi,
                              "/v1/images",
                              "/v1/images/detail",
                              "/v2/images",
                              "/v2/images/detail",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(GlanceImageByIdApi,
                              "/v1/images/<id>",
                              "/v2/images/<id>",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(GlanceImageByDockerNameApi,
                              "/v1/images/<owner>/<container>",
                              "/v2/images/<owner>/<container>",
                              resource_class_kwargs={'api': self})

    def _start_flask(self):
        LOG.info("Starting %s endpoint @ http://%s:%d" % ("GlanceDummyApi", self.ip, self.port))
        if self.app is not None:
            self.app.before_request(self.dump_playbook)
            self.app.run(self.ip, self.port, debug=True, use_reloader=False)


class Shutdown(Resource):
    def get(self):
        LOG.debug(("%s is beeing shut down") % (__name__))
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()


class GlanceListApiVersions(Resource):
    def get(self):
        LOG.debug("API CALL: %s GET" % str(self.__class__.__name__))
        resp = dict()
        resp['versions'] = dict()
        versions = [{
            "status": "CURRENT",
            "id": "v2",
            "links": [
                {
                    "href": request.url_root + '/v2',
                    "rel": "self"
                }
            ]
        }]
        resp['versions'] = versions
        return Response(json.dumps(resp), status=200, mimetype='application/json')


class GlanceSchema(Resource):
    def get(self):
        LOG.debug("API CALL: %s GET" % str(self.__class__.__name__))
        resp = dict()
        resp['name'] = 'someImageName'
        resp['properties'] = dict()
        # just an ugly hack to allow the openstack client to work
        return Response(json.dumps(resp), status=200, mimetype='application/json')


class GlanceListImagesApi(Resource):
    def __init__(self, api):
        self.api = api

    def get(self):
        LOG.debug("API CALL: %s GET" % str(self.__class__.__name__))
        try:           
            resp = dict()
            resp['next'] = None
            resp['first'] = "/v2/images"
            resp['schema'] = "/v2/schemas/images"
            resp['images'] = list()
            limit = 18
            c = 0
            for image in self.api.compute.images.values():
                f = dict()
                f['id'] = image.id
                f['name'] = str(image.name).replace(":latest", "")
                f['checksum'] = "2dad48f09e2a447a9bf852bcd93548c1"
                f['container_format'] = "docker"
                f['disk_format'] = "raw"
                f['size'] = 1
                f['created_at'] = "2016-03-15T15:09:07.000000"
                f['deleted'] = False
                f['deleted_at'] = None
                f['is_public'] = True
                f['min_disk'] = 1
                f['min_ram'] = 128
                f['owner'] = "3dad48f09e2a447a9bf852bcd93548c1"
                f['properties'] = {}
                f['protected'] = False
                f['status'] = "active"
                f['updated_at'] = "2016-03-15T15:09:07.000000"
                f['virtual_size'] = 1
                f['marker'] = None
                resp['images'].append(f)
                c += 1
                if c > limit:  # ugly hack to stop buggy glance client to do infinite requests
                    break
            if "marker" in request.args:  # ugly hack to fix pageination of openstack client
                resp['images'] = None
            return Response(json.dumps(resp), status=200, mimetype="application/json")

        except Exception as ex:
            LOG.exception(u"%s: Could not retrieve the list of images." % __name__)
            return ex.message, 500

    def post(self):
        """
        This one is a real fake! It does not really create anything and the mentioned image
        should already be registered with Docker. However, this function returns a reply that looks
        like the image was just created to make orchestrators, like OSM, happy.
        """
        LOG.debug("API CALL: %s POST" % str(self.__class__.__name__))
        body_data = json.loads(request.data)
        # lets see what we should create
        img_name = request.headers.get("X-Image-Meta-Name")
        img_size = request.headers.get("X-Image-Meta-Size")
        img_disk_format = request.headers.get("X-Image-Meta-Disk-Format")
        img_is_public = request.headers.get("X-Image-Meta-Is-Public")
        img_container_format = request.headers.get("X-Image-Meta-Container-Format")
        # try to use body payload if header fields are empty
        if img_name is None:
            img_name = body_data.get("name")
            img_size = 1234
            img_disk_format = body_data.get("disk_format")
            img_is_public = True if "public" in body_data.get("visibility") else False
            img_container_format = body_data.get("container_format")
        # try to find ID of already existing image (matched by name)
        img_id = None
        for image in self.api.compute.images.values():
            if str(img_name) in image.name:
                img_id = image.id
        LOG.debug("Image name: %s" % img_name)
        LOG.debug("Image id: %s" % img_id)
        # build a response body that looks like a real one
        resp = dict()
        f = dict()
        f['id'] = img_id
        f['name'] = img_name
        f['checksum'] = "2dad48f09e2a447a9bf852bcd93548c1"
        f['container_format'] = img_container_format
        f['disk_format'] = img_disk_format
        f['size'] = img_size
        f['created_at'] = "2016-03-15T15:09:07.000000"
        f['deleted'] = False
        f['deleted_at'] = None
        f['is_public'] = img_is_public
        f['min_disk'] = 1
        f['min_ram'] = 128
        f['owner'] = "3dad48f09e2a447a9bf852bcd93548c1"
        f['properties'] = {}
        f['protected'] = False
        f['status'] = "active"
        f['updated_at'] = "2016-03-15T15:09:07.000000"
        f['virtual_size'] = 1
        resp['image'] = f
        # build actual response with headers and everything
        r = Response(json.dumps(resp), status=201, mimetype="application/json")
        r.headers.add("Location", "http://%s:%d/v1/images/%s" % (self.api.ip,
                                                                 self.api.port,
                                                                 img_id))
        return r


class GlanceImageByIdApi(Resource):
    def __init__(self, api):
        self.api = api

    def get(self, id):
        LOG.debug("API CALL: %s GET" % str(self.__class__.__name__))
        try:
            resp = dict()
            for image in self.api.compute.images.values():
                if image.id == id or image.name == id:
                    resp['id'] = image.id
                    resp['name'] = image.name

                    return Response(json.dumps(resp), status=200, mimetype="application/json")

            response = Response("Image with id or name %s does not exists." % id, status=404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

        except Exception as ex:
            LOG.exception(u"%s: Could not retrieve image with id %s." % (__name__, id))
            return Response(ex.message, status=500, mimetype='application/json')

    def put(self, id):
        LOG.debug("API CALL: %s " % str(self.__class__.__name__))
        LOG.warning("Endpoint not implemented")
        return None


class GlanceImageByDockerNameApi(Resource):
    def __init__(self, api):
        self.api = api

    def get(self, owner, container):
        logging.debug("API CALL: %s GET" % str(self.__class__.__name__))
        try:
            name = "%s/%s" % (owner, container)
            if name in self.api.compute.images:
                image = self.api.compute.images[name]
                resp = dict()
                resp['id'] = image.id
                resp['name'] = image.name
                return Response(json.dumps(resp), status=200, mimetype="application/json")

            response = Response("Image with id or name %s does not exists." % id, status=404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

        except Exception as ex:
            logging.exception(u"%s: Could not retrieve image with id %s." % (__name__, id))
            return Response(ex.message, status=500, mimetype='application/json')
