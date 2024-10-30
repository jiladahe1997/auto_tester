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
