import os
import requests
import json
import glob
import re
from concurrent.futures import ThreadPoolExecutor
# import pprint


# 定义TengxunVidio类
class TengxunVidio(object):
    # 通过函数get_m3u8获得m3u8文件的url头部、ts片段列表的url和视频标题
    @staticmethod
    def get_m3u8():
        if not os.path.exists("vidio"):
            os.mkdir("vidio")
        if not os.path.exists("ts_fragment"):
            os.mkdir("ts_fragment")
        data = input("请粘贴data：")
        headers = {
            # 若是有会员，可加上cookie可下载vip视频
            "origin": "https://v.qq.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "referer": "https://v.qq.com/",
        }
        url = "https://v.qq.com/x/page/w322962ks7q.html"
        resp = requests.post(url, data=data, headers=headers)
        resp.encoding = "utf-8"
        resp1 = resp.json()
        # pprint.pprint(resp1)
        resp.close()
        vinfo = resp1['vinfo']
        vinfo = json.loads(vinfo)
        # pprint.pprint(vinfo2)
        # m3u8 = vinfo['vl']['vi'][0]['ul']['m3u8']
        url3 = vinfo['vl']['vi'][0]['ul']['ui'][0]['url']
        title0 = vinfo['vl']['vi'][0]['ti']
        print("正在下载：", title0)
        title = re.sub(r'[\\/:*?"<>|\n]', '_', title0)
        # print(url3)
        head = url3.rsplit("/", 1)[0]
        m3u8 = requests.get(url3).content
        m3u8 = str(m3u8)
        m3u8 = m3u8.split("\\n")[1:-1]
        m3u8_list = []
        for line in m3u8:
            if line.startswith("#"):
                continue
            m3u8_list.append(line)
        # print(m3u8)
        # print("拿到m3u8文件")
        return head, m3u8_list, title

    # 下载所有ts文件，文件名以便排序，防止视频片段顺序错误
    @staticmethod
    def download_ts(m3u8_url, head):
        url2 = head + "/" + m3u8_url
        response = requests.get(url2).content
        min_title = m3u8_url.split('_', 1)[0] + ".ts"
        while len(min_title) < 7:
            min_title = "0" + min_title
        with open("ts_fragment/" + min_title, mode='wb') as f1:
            f1.write(response)

    # 合并所有ts文件=>video下的一个ts文件，并删除文件夹ts_fragment下所有ts文件
    @staticmethod
    def ts_add(title):
        ts_list = glob.glob('ts_fragment/*.ts')
        print("正在处理…", len(ts_list), "个ts文件")
        with open(f"vidio/{title}.ts", mode="wb") as f1:
            for i in ts_list:  # 循环读取同文件夹下的ts文件
                f2 = open(i, mode='rb')
                f1.write(f2.read())
                f2.close()
                os.remove(i)
        print("下载完成！", title)


if __name__ == '__main__':
    while True:
        head, m3u8_list, title = TengxunVidio.get_m3u8()
        # print(m3u8_list)
        pool = ThreadPoolExecutor(100)
        for m3u8_url in m3u8_list:
            pool.submit(TengxunVidio.download_ts, m3u8_url, head)
        pool.shutdown(wait=True)
        TengxunVidio.ts_add(title)