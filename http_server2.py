import json
import time
import numpy as np
from twisted.web import server, resource
from twisted.internet import reactor, endpoints

from _2Dto3D import pixel_to_world
from _motor import Motor


# 像素坐标转载具坐标
def tray_coordinate(data):
    result_camera_list = []
    for camera in data['cameraList']:
        result_camera = {'cameraDirection': camera['cameraDirection'],
                         'dataSize': camera['dataSize'],
                         'dataList': []}
        camera_parameter = camera['cameraParameter']
        f = camera_parameter["f"]
        c = camera_parameter["c"]
        camera_intrinsic = np.mat(np.zeros((3, 3), dtype=np.float64))
        camera_intrinsic[0, 0] = f[0]
        camera_intrinsic[1, 1] = f[1]
        camera_intrinsic[0, 2] = c[0]
        camera_intrinsic[1, 2] = c[1]
        camera_intrinsic[2, 2] = np.float64(1)
        r = camera_parameter["R"]
        t = np.asmatrix(camera_parameter["T"]).T

        for camera_data in camera['dataList']:
            result_data = {'analysisType': camera_data['analysisType'],
                           'pointSize': camera_data['pointSize'],
                           'pointRegion': []}

            points_2d = np.empty(shape=(0, 2), dtype=np.double)
            for camera_data_point in camera_data['pointRegion']:
                points_2d = np.vstack((points_2d, [camera_data_point['x'], camera_data_point['y']]))
            points_3d = pixel_to_world(camera_intrinsic, r, t, points_2d)
            for point_3d in points_3d:
                result_point = {'x': point_3d[0], 'y': point_3d[1], 'z': point_3d[2]}
                result_data['pointRegion'].append(result_point)
            result_camera['dataList'].append(result_data)

    return {"code": 200, "message": "操作成功",
            "data": {"cameraList": result_camera_list}}


# 载具坐标转工位坐标
def op_coordinate(data):
    # data['stationSpace']
    lock_space = data['lockSwitchCoordinate']
    barcode_space = data['QRToLock']
    bias = {'x':0.0, 'y':0.0, 'z':0.0} #data['bias']

    barcode_space['x'] = barcode_space['x'] - lock_space['x']
    barcode_space['y'] = barcode_space['y'] - lock_space['y']
    barcode_space['z'] = barcode_space['z'] - lock_space['z']
    op_objs = []
    for data_obj in data['dataList']:
        op_obj = {'analysisType': data_obj['analysisType']}
        op_obj['pointSize'] = data_obj['pointSize']
        data_point_region = data_obj['pointRegion']
        op_point_region = []
        for data_point in data_point_region:
            op_point = {'x': data_point['x'] - barcode_space['x'] + bias['x'],
                        'y': data_point['y'] - barcode_space['y'] + bias['y'],
                        'z': data_point['z'] - barcode_space['z'] + bias['z']}
            op_point_region.append(op_point)
        op_obj['pointRegion'] = op_point_region

        op_objs.append(op_obj)

    return {"code": 200, "message": "操作成功",
            "data": {"dataSize": data['dataSize'], "dataList": op_objs}}


# 工位坐标转加工坐标
def motor_coordinate(data):
    bias = {'x':0.0, 'y':0.0, 'z':0.0} #data['bias']

    # 所有电机
    motor_objs = []
    for motor_obj in data['motorList']:
        motor_coord = motor_obj['motorCoordinate']
    # 所有工位的目标点
        for data_obj in data['dataList']:
            motor_obj = {'motorType': motor_obj['motorType']}
            motor_obj['pointSize'] = data_obj['pointSize']
            data_point_region = data_obj['pointRegion']
            op_point_regionx = []
            op_point_regiony = []
            op_point_regionz = []
            for data_point in data_point_region:
                op_pointx = {'x': data_point['x'] - motor_coord['x'] + bias['x']}
                op_point_regionx.append(op_pointx)
                op_pointy = {'y': data_point['y'] - motor_coord['y'] + bias['y']}
                op_point_regiony.append(op_pointy)
                op_pointz = {'z': data_point['z'] - motor_coord['z'] + bias['z']}
                op_point_regionz.append(op_pointz)
            motor_obj['pointRegionX'] = op_point_regionx
            motor_obj['pointRegionY'] = op_point_regiony
            motor_obj['pointRegionZ'] = op_point_regionz

        motor_objs.append(motor_obj)

    return {"code": 200, "message": "操作成功",
            "data": {"dataSize": data['dataSize'], "dataList": motor_objs}}


class Counter(resource.Resource):
    isLeaf = True  # important

    def __init__(self):
        pass

    def render_GET(self, request):
        print(dir(request))
        request.setHeader(b"content-type", b"text/plain")
        request.setResponseCode(404)
        return b''

    def render_POST(self, request):
        body = request.content.read()  # 获取信息

        request.setHeader(b"content-type", b"application/json")
        try:
            data = json.loads(body.decode())
        except Exception as e:
            print('json loads exception:', e)
            request.setResponseCode(400)
            return b''

        uri = request.uri.rstrip(b'/')
        if uri == b'/api/coordinate/tray':  # 载具坐标
            print('像素坐标转载具坐标')
            result = tray_coordinate(data)
        elif uri == b'/api/coordinate/op':  # 工位坐标
            print('载具坐标转工位坐标')
            result = op_coordinate(data)
        elif uri == b'/api/coordinate/motor':  # 加工坐标
            print('工位坐标转加工坐标')
            result = motor_coordinate(data)
        else:
            result = {"code": 400, "message": "无效的api@{}".format(uri.decode())}

        return json.dumps(result).encode("utf-8")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    endpoints.serverFromString(reactor, "tcp:8012").listen(server.Site(Counter()))
    reactor.run()
