import subprocess
import time
import platform
import speedtest
import logging
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.text import MIMEText

def ping(host, count=4):
    """检测到目标IP的连通性和延迟"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, str(count), host]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
        # 提取平均延迟（不同系统格式不同，需自行解析）
        avg_latency = "N/A"
        if '平均' in output:  # Windows中文系统
            avg_latency = output.split('平均 = ')[1].split('ms')[0]
        elif 'rtt' in output:  # Linux/Mac系统
            avg_latency = output.split('rtt min/avg/max/mdev = ')[1].split('/')[1]
        return True, float(avg_latency)
    except subprocess.CalledProcessError:
        return False, None

# 测试路由器和外网连通性
router_online, router_latency = ping("192.168.1.1")  # 替换为你的路由器IP
internet_online, internet_latency = ping("8.8.8.8")  # Google DNS

print(f"路由器状态: {'在线' if router_online else '离线'}, 延迟: {router_latency}ms")
print(f"外网状态: {'在线' if internet_online else '离线'}, 延迟: {internet_latency}ms")


# 使用speedtest库测试带宽
def speed_test():
    """使用speedtest库测试带宽"""
    st = speedtest.Speedtest()
    st.download()  # 下载速度（bps）
    st.upload()    # 上传速度
    return st.results.dict()  # 返回详细结果

result = speed_test()
print(f"下载速度: {result['download'] / 1e6:.2f} Mbps")
print(f"上传速度: {result['upload'] / 1e6:.2f} Mbps")

# 测试丢包率
def packet_loss_test(host="8.8.8.8", count=20):
    """连续Ping测试丢包率"""
    success = 0
    for _ in range(count):
        if ping(host, count=1)[0]:
            success += 1
    return (count - success) / count * 100  # 丢包率百分比

loss_rate = packet_loss_test()
print(f"丢包率: {loss_rate:.1f}%")


logging.basicConfig(
    filename='network_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# 记录日志
def log_status():
    status, latency = ping("8.8.8.8")
    if not status:
        logging.error("网络断开！")
    elif latency > 100:  # 延迟高于100ms记录警告
        logging.warning(f"高延迟: {latency}ms")

log_status()


# 异常通知（邮件示例）
def send_alert(email, password, message):
    msg = MIMEText(message)
    msg['Subject'] = '网络异常警报'
    msg['From'] = email
    msg['To'] = email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(email, password)
        server.sendmail(email, [email], msg.as_string())

# 使用示例（需开启SMTP服务）
# send_alert('your_email@gmail.com', 'your_password', '检测到网络断开！')

# 重启路由器（需要路由器支持）
def reboot_router(router_ip, username, password):
    """通过API重启路由器（仅支持特定型号）"""
    url = f"http://{router_ip}/api/reboot"
    try:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(username, password),
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

# 使用前需查阅路由器API文档


# 完整监控脚本框架
def main_monitor():
    while True:
        # 基础检测
        router_ok, _ = ping("192.168.1.1")
        internet_ok, latency = ping("8.8.8.8")
        
        # 逻辑判断
        if not router_ok:
            logging.error("路由器离线！")
            send_alert("路由器不可达")
        elif not internet_ok:
            logging.error("外网断开！")
            send_alert("无法连接互联网")
        elif latency > 150:
            logging.warning(f"高延迟: {latency}ms")
        
        # 每5分钟检测一次
        time.sleep(300)

if __name__ == "__main__":
    main_monitor()