#导入paramiko包
import paramiko
#导入StringIO模块
from io import StringIO
import time
import os

ssh = None


def sshClientInit():
    try:
        # 创建sshClient实例对象
        ssh = paramiko.SSHClient()
        # 设置信任远程机器，允许访问
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #set_missing_host_key_policy
        '''
        设置远程服务器没有在know_hosts文件中记录时的应对策略。目前支持三种策略：
        AutoAddPolicy 自动添加主机名及主机密钥到本地HostKeys对象，不依赖load_system_host_key的配置。即新建立ssh连接时不需要再输入yes或no进行确认
        WarningPolicy 用于记录一个未知的主机密钥的python警告。并接受，功能上和AutoAddPolicy类似，但是会提示是新连接
        RejectPolicy 自动拒绝未知的主机名和密钥，依赖load_system_host_key的配置。此为默认选项
        '''
    except:
        print("There is an error with the SSHClient")
        ssh = None


def sshConnect():
    if (ssh == None):
        print("SSHClient init failed....")
    try:
        # 设置ssh远程连接机器，参数依次为地址、端口、用户名、密码,ssh端口默认22
        ssh.connect("192.168.211.100", "22", "root", "")
        '''
        connect参数详解：
        hostname 连接的目标主机，该项必填
        port=SSH_PORT 指定端口
        username=None 验证的用户名
        password=None 验证的用户密码
        pkey=None 私钥方式用于身份验证
        key_filename=None 一个文件名或文件列表，指定私钥文件
        timeout=None 可选的tcp连接超时时间
        allow_agent=True, 是否允许连接到ssh代理，默认为True 允许
        look_for_keys=True 是否在.ssh文件夹中搜索私钥文件，默认为True 允许
        compress=False, 是否打开压缩
        '''
        '''
        基于密钥连接
        关于SSH密钥链接大家可以参考我的这篇博客:https://www.cnblogs.com/victoryhan/p/16417898.html
        这里只专注于客户端Python代码的实现。
        #导入私钥
        privateKey = paramiko.RSAKey.from_private_key_file('./id_rsa')
        ssh.connect('ip',22,'username',pkey=privateKey)
        '''
        '''
        基于私钥字符串连接
        #私钥字符串就是私钥的内容，位置在这篇博文里有介绍：https://www.cnblogs.com/victoryhan/p/16417898.html
        keyStr = '[私钥内容]'
        privateKey = paramiko.RSAKey(file_obj=StringIO(keyStr))
        ssh.connect('ip','22','username',pkey=privateKey)
        '''
    except:
        print("Failed to connect to remote server")
        time.sleep(0.5)
        sshConnect()


sshClientInit()
sshConnect()
try:
    #设置代表需要执行的linux命令的变量，多条命令用分号隔开
    order = "dtach -a /tmp/vmm;su;echo peripheral > /sys/devices/platform/soc/a800000.ssusb/mode"
    #每次执行命令会返回三个对象，对应标准输入、标准输出、标准错误。每调用一次exec_command方法就相当于重新打开一次linux终端，终端环境都是新的。
    stdin, stdout, stderr = ssh.exec_command(order)
    out = stdout.readlines()
    #如果使用了sudo命令请启用下面的代码并填入对应的密码
    #stdin.write("passwd")
    #stdin.flush()
    #打印输出结果
    # print(stdout.readlines())
    #打印命令执行错误信息
    # print(stderr.readlines())
    os.system('adb root')
    os.system('adb remount')
    os.system('adb shell screenrecord > C:\Users\%username%\Documents\turnonVideo.mp4')
    os.system('adb logcat > C:\Users\%username%\Documents\turnonLog.log')
except:
    print('Fail to carry out command')
#关闭ssh链接
ssh.close()
