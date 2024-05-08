# -*- coding: utf-8 -*-

import serial
import serial.tools.list_ports
import logging
import time
import requests
import re
from datetime import datetime
import threading
from subprocess import Popen, PIPE
import sys
import traceback

# debug日志输出
logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(
    handlers=[logging.FileHandler(
            filename="{}.log".format(datetime.now().strftime("%m_%d_%Y_%H_%M_%S")), 
            encoding='utf-8', mode='a+')],
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

####################################################################################
# TODO：串口操作 utils工具，后期考虑移到单独的文件
# 全局变量：串口对象
COM_DEVICE_NAME = "COM17" 
ser = None
def utils_serial_write(write_str: str):
    """
    辅助函数，用于向串口发送数据，不关心回复

    :param p1: 需要想发送的数据，字符串
    :return: None
    """ 
    global ser
    logging.info(repr("serial write:[{}]".format(write_str)))
    ser.write(str.encode(write_str))
    return


def utils_serial_write_and_read(write_str: str) -> str:
    """
    辅助函数，用于向串口发送数据并从串口读取数据.

    Note: 发送后默认会等待1秒后再读取，1秒是在创建ser对象时指定的

    :param p1: 需要想发送的数据，字符串
    :return: 从串口读取到的数据。字符串
    """ 
    global ser
    logging.info(repr("serial write:[{}]".format(write_str)))
    ser.write(str.encode(write_str))
    lines = ser.readlines()
    lines_str = b''.join(lines).decode()
    logging.info(repr("serial read :[{}]".format(lines_str)))
    return lines_str



def utils_serial_open_or_close(open_or_close: bool):
    """
    辅助函数，用于打开或关闭串口

    :param open_or_close: True代表打开串口，Flase代表关闭串口
    :return: None
    """ 
    global ser
    if open_or_close == True:
        logging.info("open serial...")
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if p.device == COM_DEVICE_NAME:
                logging.info("success find serial {}".format(p.device))
                ser = serial.Serial(p.device, 115200, timeout=1)
                break
        
        if ser == None:
            raise Exception("Can not found Serial {}".format(COM_DEVICE_NAME))
    else:
        logging.info("close serial...")
        ser.close()


def utils_serial_wait_for_reboot()->bool:
    """
    辅助函数，不断的从串口读取数据，并阻塞等待重启完成
              默认超时300秒

    :return: 重启完成 True，重启超时 False
    """
    global ser
    start = time.time()
    timeout = 300
    output = b""
    logging.info("waiting for reboot ...")
    while True:
        now = time.time()
        if (now - start > timeout):
            logging.err("waiting for reboot timeout!")
            return False
        lines = ser.readlines()
        lines_str = b''.join(lines)
        output = output+lines_str
        if b"ax2000 login" in output:
            return True
        
def utils_serial_login():
    output = utils_serial_write_and_read("\n")
    
    if output == "\r\r\nBSTOS (Operation System by Black Sesame Technologies) 1.2.1.4-0.1.2 ax2000 ttyS0\r\n\r\nax2000 login: ":
        logging.info("find unlogin serial port, login ......")
        output = utils_serial_write_and_read("root\n")
        time.sleep(2)
        output = utils_serial_write_and_read("\n")
        output = utils_serial_write_and_read("\n")
        output = utils_serial_write_and_read("\n")
        output = utils_serial_write_and_read("\n")
        output = utils_serial_write_and_read("\n")
        if output == "\r\nroot@ax2000:~# ":
            logging.info("login success")
        else:
            raise Exception("login failed! serial output: {}".format(output))

    elif output == "\r\nroot@ax2000:~# ":
        logging.info("find already login serial port, skip login")

    else:
        raise Exception("find unkonw serial output: {}".format(output))
############################################################################################




















event = threading.Event()
# 创建windows上的iperf -c
def windows_iperf_client(iperf_server_ip_addr : str):
    logging.info("start windows_iperf_client ip: {}".format(iperf_server_ip_addr))
    process = Popen(['D:\iperf3.exe', 
                     '-c', iperf_server_ip_addr,
                     "-b", "1000M",
                     "-t", "46000",
                     "-P","10"], stdout=PIPE, stderr=PIPE,universal_newlines=True, bufsize=1)
    while event.is_set() != True:
        pass
    process.terminate()

def iperf_dd():
    # 设置ip地址，开启iperf -s
    output = utils_serial_write_and_read("ifconfig eth1\n")
    ip_addr = re.search("(?<=inet addr:)\d{3}\.\d{3}\.\d{1,3}.\d{1,3}",output).group()
    new_ip_addr = "192.168.3.251"
    logging.info("now ip address is: {}".format(ip_addr))
    if ip_addr != new_ip_addr:
        logging.info("setup ip address to: {}".format(new_ip_addr))
        output = utils_serial_write_and_read("ifconfig eth1 {}\n".format(new_ip_addr))
        output = utils_serial_write_and_read("ifconfig eth1\n")
        ip_addr = re.search("(?<=inet addr:)\d{3}\.\d{3}\.\d{1,3}.\d{1,3}",output).group()
        if ip_addr != new_ip_addr:
            raise Exception("ip set failed! serial output: {}".format(output))
    output = utils_serial_write_and_read("./iperf3 -s > iperf.log &\n")

    # windows开启iperf -c
    event.clear()
    thread  = threading.Thread(target=windows_iperf_client, args=(new_ip_addr,))
    thread.start()

    # 开启dd命令
    output = utils_serial_write_and_read("ls /dev/disk/by-uuid\n")
    sd_card_size = re.search("013fb870-ea4f-4bc9-ab41-e52d16a0b2a3", output)
    if sd_card_size is None:
        raise Exception("can not find sd card: {}".format(output))
    output = utils_serial_write_and_read("umount /dev/disk/by-uuid/013fb870-ea4f-4bc9-ab41-e52d16a0b2a3\n")
    output = utils_serial_write_and_read("mount -U 013fb870-ea4f-4bc9-ab41-e52d16a0b2a3 /mnt/media/rmr_test/\n")
    output = utils_serial_write_and_read("./dd_test.sh /mnt/media/rmr_test > dd.log 2>&1  &\n")
    
    # 等待60秒后取消测试
    time.sleep(60)
    # windows关闭iperf -c
    event.set()
    output = utils_serial_write_and_read("ps -ef | grep \"/bin/sh ./dd_test.sh\" | grep -v grep | awk 'FNR == 1 {print $2}' | xargs kill -9\n")
    output = utils_serial_write_and_read("ps -ef | grep \"dd if=/dev/zero\" | grep -v grep | awk 'FNR == 1 {print $2}' | xargs kill -9\n")

def do_test()->bool:
    #1.打开并检查串口
    utils_serial_open_or_close(True)

    # 2.登录系统
    utils_serial_login()

    # 3.执行测试命令
    output = utils_serial_write_and_read("ifconfig eth1\n")
    ip_addr = re.search("(?<=inet addr:)\d{3}\.\d{3}\.\d{1,3}.\d{1,3}",output).group()
    new_ip_addr = "192.168.3.251"
    logging.info("now ip address is: {}".format(ip_addr))
    if ip_addr != new_ip_addr:
        logging.info("setup ip address to: {}".format(new_ip_addr))
        output = utils_serial_write_and_read("ifconfig eth1 {}\n".format(new_ip_addr))
        output = utils_serial_write_and_read("ifconfig eth1\n")
        ip_addr = re.search("(?<=inet addr:)\d{3}\.\d{3}\.\d{1,3}.\d{1,3}",output).group()
        if ip_addr != new_ip_addr:
            raise Exception("ip set failed! serial output: {}".format(output))

    count=0
    app_loop_count = 1
    while count < app_loop_count:
        count+=1
        # 等待10秒
        time.sleep(10)
        # 清空dmesg日志
        output = utils_serial_write_and_read("./dmesg > /userdata/startup_dmesg.log\n")
        output = utils_serial_write_and_read("./dmesg -C\n")

        # 启动客户app
        output = utils_serial_write_and_read("cd /usr/idbApp; ./idb_MainApp > /dev/null 2>&1 &\n")
        time.sleep(2)
        output = utils_serial_write_and_read("cd /usr/bsdApp; ./run_bsd_app.sh > /dev/null 2>&1 &\n")
        time.sleep(1)
        output = utils_serial_write_and_read("cd /usr/aebApp/raimo/; ./start_raimo.sh > /dev/null 2>&1 &\n")
        output = utils_serial_write_and_read("cd ~\n")
        output = utils_serial_write_and_read("./stress -c 8 > /dev/null 2>&1 &\n")

        # 开启dmesg日志，并等待120秒
        time.sleep(1)
        time.sleep(120)
        #utils_serial_write("./dmesg -w | grep -v \"is_camera_locked\|deser_misc\|rmr\"\n")
        output = utils_serial_write("./dmesg | grep -v \"is_camera_locked\|deser_misc\|rmr\"\n")
        start = time.time()
        timeout = 10
        dmesg_output = ""
        while time.time() - start < timeout:
            lines = ser.readlines()
            try:
                 lines_str = b''.join(lines).decode()
                 dmesg_output = dmesg_output+lines_str
            except:
                 logging.warn("find unexpect char in line:")
                 logging.warn(lines)
                 logging.warn("all output:")
                 logging.warn(dmesg_output)
                 utils_serial_open_or_close(False)
                 return False



        # # 4.检查测试结果
        output = utils_serial_write_and_read("\x03")
        logs = dmesg_output.split("\r\n")

        logging.info(logs)
        for log in logs:
            # 这条日志是否正确
            # 跳过空行
            if log == "":
                continue

            ### 判断方法1，有无xhci
            if "xhci" in log:
                correct = False
            else :
                correct = True

            ### 判断方法2：白名单
            # correct = False
            # for OK_log in (OK_logs + OK_logs_when_exit):
            #     if OK_log in log:
            #         correct = True
            #         break
            
            if correct == False:
                # 找到有问题的日志，问题复现
                logging.error("find err log:[{}]".format(log))
                utils_serial_open_or_close(False)
                return False

        # # 清空dmesg日志
        # output = utils_serial_write_and_read("./dmesg -C\n")

        # 关闭用户app，再次测试
        output = utils_serial_write_and_read("/usr/bsdApp/kill_ax2000_pid.sh\n")

    
    utils_serial_open_or_close(False)
    return True
        















def main():
    # 开始重启一次
    utils_serial_open_or_close(True)
    utils_serial_write_and_read("\n")
    utils_serial_write_and_read("\n")

    utils_serial_login()
    utils_serial_write_and_read("\x03")
    utils_serial_write_and_read("\x03")
    utils_serial_write_and_read("\n")
    utils_serial_write_and_read("\n")
    utils_serial_write("reboot\n")
    if utils_serial_wait_for_reboot() is False:
        raise Exception("wait reboot timeout!")
    time.sleep(10)
    utils_serial_write_and_read("\n")
    utils_serial_write_and_read("\n")
    utils_serial_open_or_close(False)





    # 主入口
    count = 1
    maxcount=10000
    while count < maxcount:
        logging.info("测试次数 {}/{}".format(count, maxcount))
        count+=1
        ret = do_test()
        if ret==True:
            #重启再次测试
            utils_serial_open_or_close(True)
            utils_serial_write_and_read("\x03")
            utils_serial_write_and_read("\x03")
            utils_serial_write_and_read("\n")
            utils_serial_write_and_read("\n")
            utils_serial_write("reboot\n")
            if utils_serial_wait_for_reboot() is False:
                raise Exception("wait reboot timeout!")

            time.sleep(10)
            utils_serial_write_and_read("\n")
            utils_serial_write_and_read("\n")
            utils_serial_open_or_close(False)
        else:
            url = 'https://open.feishu.cn/open-apis/bot/v2/hook/8372a369-ee77-4a34-ab19-3b061661e5c4'
            myobj = {
                "msg_type": "text",
                "content": {
                    "text": "auto_tester检测到用例失败，请查看！ {}".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
                }
            }
            requests.post(url, json = myobj)
            exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
            logging.error(traceback.format_exc())
            url = 'https://open.feishu.cn/open-apis/bot/v2/hook/8372a369-ee77-4a34-ab19-3b061661e5c4'
            myobj = {
                "msg_type": "text",
                "content": {
                    "text": "auto_tester运行错误，请查看！ {}".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
                }
            }
            x = requests.post(url, json = myobj)
            exit()
