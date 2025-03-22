from cgi import print_arguments
from cmath import cos, pi, sin, atan
from geopy.distance import distance

import json
import math

sourceFile = "./DataFile/Variflight_MU5735_20220321-xls.json"
resFile = "./DataFile/Variflight_MU5735_20220321-ext.json"

EARTH_REDIUS = 6378.137


#计算单位弧度距离
def rad(d):
    return d * pi / 180.0


#计算两个坐标之前的直线距离，单位km
def getDistance(lat1, lng1, lat2, lng2):
    radLat1 = rad(lat1)
    radLat2 = rad(lat2)
    a = radLat1 - radLat2
    b = rad(lng1) - rad(lng2)
    s = 2 * math.asin(
        math.sqrt(
            math.pow(sin(a / 2), 2) +
            cos(radLat1) * cos(radLat2) * math.pow(sin(b / 2), 2)))
    s = s * EARTH_REDIUS
    return s


#采用geopy库计算两组经纬度之间的距离对象
def getDistanceFromGPS(lat1, lng1, lat2, lng2):
    prePoint = (float(lat1), float(lng1))
    nextPoint = (float(lat2), float(lng2))
    return distance(prePoint, nextPoint)


fo = open(sourceFile, "r")
jsonData = json.load(fo)
fo.flush()
fo.close()

arrayLen = len(jsonData)
i = 0
while (i < arrayLen):
    if i == 0:  #第一个坐标无需计算和上一个坐标的直线距离
        jsonData[i]["distance"] = 0
    else:  #第二个坐标开始计算当前坐标和上一个坐标的直线距离
        # jsonData[i]["distance"] = getDistance(jsonData[i]["latitude"],
        #                                       jsonData[i]["longitude"],
        #                                       jsonData[i - 1]["latitude"],
        #                                       jsonData[i - 1]["longitude"])

        jsonData[i]["distance"] = getDistanceFromGPS(
            jsonData[i - 1]["latitude"], jsonData[i - 1]["longitude"],
            jsonData[i]["latitude"], jsonData[i]["longitude"]).meters

    if jsonData[i]["Time"] < 1647843661:  #所有第一个下降高度之前的坐标忽略飞机方向与垂直的夹角
        jsonData[i]["angle"] = 90
    else:  #从飞机下降高度的第一个坐标开始计算飞机方向与垂直现的夹角，基于当前位置和前一个坐标的距离和高度差计算tan-1
        hightSpan = jsonData[i - 1]["height"] - jsonData[i]["height"]
        jsonData[i]["angle"] = 180 / pi * atan(
            jsonData[i]["distance"] / hightSpan).real
    i = i + 1
fo = open(resFile, "w")
fo.write(json.dumps(jsonData))
fo.flush()
fo.close()