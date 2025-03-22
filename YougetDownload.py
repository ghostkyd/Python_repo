import sys
from you_get import common as you_get

#设置下载目录
directory= r'D:\BaiYaopu'
#需要下载的视频地址
url = 'https://www.bilibili.com/bangumi/play/ep115520?from_spmid=666.19.0.0'
#cookie所在地址
cookies = r'C:\Users\tssh\AppData\Roaming\Mozilla\Firefox\Profiles\pia527rj.default-release\cookies.sqlite'
print('you-get','--playlist','-c', cookies , '-o' , directory, url)