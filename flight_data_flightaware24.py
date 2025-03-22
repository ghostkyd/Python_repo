from cmath import pi, atan
from geopy.distance import distance
from datetime import datetime
import openpyxl
import time
import datetime

unitMeter = 0.3048  #1英尺=0.3048米
sourceFile = "./DataFile/MU5735-Flightradar24-Granular-Data.xlsx"


#采用geopy库计算两组经纬度之间的距离对象
def getDistanceFromGPS(lat1, lng1, lat2, lng2):
    prePoint = (float(lat1), float(lng1))
    nextPoint = (float(lat2), float(lng2))
    return distance(prePoint, nextPoint)


#时间字符串转换为时间戳，返回浮点类型
def timespamFromDtstring(timeStr):
    dttime = datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%SZ.%f")
    return dttime.timestamp()


def getAngle(hight, distance):
    return 180 / pi * atan(hight / distance).real


def ftminTometersec(ftValue):
    return ftValue / 60 * unitMeter


print("\033c")
print("开始数据处理......")
t1 = time.time()
data_book = openpyxl.load_workbook(sourceFile, read_only=False, data_only=True)
print(data_book.sheetnames)
data_sheet = data_book["MU5735-Flightradar24-Granular-D"]
prevTime = time.time()
nextTime = time.time()
index = 0
data_cells = data_sheet["A2":"M363"]
data_len = len(data_cells)
i = 0
while i < data_len:
    if (i == 0):
        data_cells[i][11].value = 0
        data_cells[i][12].value = 0
    else:
        dltTime = timespamFromDtstring(
            data_cells[i][0].value) - timespamFromDtstring(
                data_cells[i - 1][0].value)
        dltHight = data_cells[i][6].value - data_cells[i - 1][6].value
        dltDis = getDistanceFromGPS(data_cells[i][3].value,
                                    data_cells[i][4].value,
                                    data_cells[i - 1][3].value,
                                    data_cells[i - 1][4].value).meters
        if (dltDis == 0):
            data_cells[i][11].value = data_cells[i - 1][11].value
        else:
            data_cells[i][11].value = getAngle(dltHight, dltDis)
        v1 = ftminTometersec(data_cells[i][10].value)
        v2 = ftminTometersec(data_cells[i - 1][10].value)
        data_cells[i][12].value = (float)(v1 - v2) / dltTime
    i = i + 1

data_book.save(sourceFile)
data_book.close
t2 = time.time()
print(data_len, "条数据处理完毕，全程耗时:", (t2 - t1) * 1000, "毫秒")