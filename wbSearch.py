from codecs import Codec
import os
import time

# keyWord = "2867129695"
# filePath = r"E:\sgk\kz\6.9更新总库.txt"

# keyWord = "18616907917"
# filePath = r"E:\sgk\kz\wb2019.txt"

keyWord = "jd_65301198b7447"
filePath = r"E:\sgk\www_jd_com_12g.txt"


BLOCK_SIZE = 1024
LF = "\n"
CR = "\r"

def read_in_block(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            block = f.read(BLOCK_SIZE)  #每次读取固定长度到内存缓冲区
            if block:
                yield block
            else:
                return  #如果读取到文件末尾，则退出

stime = time.time()
count = 0
for blk in read_in_block(filePath):
    count = count + 1
    index = blk.find(keyWord)
    if (index != -1):
        realVal = blk[index:]
        lfIndex = realVal.find(LF)
        print("The key word data: ", realVal[0:lfIndex])
        break

print("Job is Done...")
etime = time.time()
print("Read data block count: ", count)
print("Process time: ", str(etime - stime), "seconds...")
