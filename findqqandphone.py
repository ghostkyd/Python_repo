from codecs import Codec
import email
import os
import time

keyWord = "jd_65301198b7447"
filePath = r"E:\sgk\www_jd_com_12g.txt"


def read_in_block(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            block = f.readline()  #每次读取固定长度到内存缓冲区
            if block:
                yield block
            else:
                return  #如果读取到文件末尾，则退出


stime = time.time()
for blk in read_in_block(filePath):
    strarr = blk.split('---')
    name = strarr[0]
    if ('王启嘉' == name):
        print(blk)
        break

print("Searching is complete...")
etime = time.time()
print("Process time: ", str(etime - stime), "seconds...")