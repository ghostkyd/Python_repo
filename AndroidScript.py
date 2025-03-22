import time
from appium import webdriver

#基础信息配置
desired_caps = {
    "platformName": "Android",
    "deviceName": "1cab48c2",
    "platformVersion": "11",
    "appPackage": "com.tencent.mm",
    "appActivity": "com.tencent.mm.ui.LauncherUI",
    "noReset": "true"
}

#向下滑动
def swipe_down(driver,t=500,n=1):
    s = driver.get_window_size()
    x1 = s['width'] * 0.5  # x坐标
    y1 = s['height'] * 0.25 # 起点y坐标
    y2 = s['height'] * 0.75 # 终点y坐标
    for i in range(n):
        driver.swipe(x1,y1,x1,y2,t)

driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub',desired_caps)  # 启动app
time.sleep(8)
swipe_down(driver)
time.sleep(5)
driver.find_element_by_id("com.tencent.mm:id/f1v").click()
time.sleep(4)
# driver.find_element_by_xpath('//*[@text="去结算"]').click()