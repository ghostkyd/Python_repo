import random
import numpy as np


def is_contain(arr, num):
    # 使用 in1d 方法判断
    if np.in1d(arr, num).any():
        return False
    else:
        return True

red_num=[]
blue_num=0

while(len(red_num)<6):
    num = random.randint(1, 33)
    if (is_contain(red_num,num)):
        red_num.append(num)

blue_num=random.randint(1, 16)

sorted_red=sorted(red_num)
print("红球：",sorted_red)
print("篮球：",blue_num)
