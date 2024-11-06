# 简介


此项目是一个脚本程序，主要用途是复现需要挂机长时间触发各类问题，解放你的双手，有更多时间去做更有意义的事情。


<br/>
<br/>
<br/>

# 背景介绍
在嵌入式开发过程中，经常会遇到***偶现***的问题，例如我本人在开发过程就遇到过：
 - 跑10个小时，系统挂了
 - 重启过程中，偶现系统挂了
 - 跑某个业务，有概率导致USB挂了

解决这种问题时，我们需要从两个方面下手：
1. 如何定位问题。
    - 很多时候，这种偶现问题可能是由于并发、竞态、未加锁造成的。所以其实很难真正从问题发生时的现场，反向推导出问题根因。  大部分时候都是根据怀疑点来修改代码。

2. 如何验证问题解决。
    - 如上所述，由于无法100%确定问题点。 但是可以根据原场景复现回归的方法，来确保问题解决。
    - 由于嵌入式环境复杂，甚至完全一致的单板上，根据PCB制造的工艺区分，表现都有可能不同。


综上所述，本项目提出了一种针对上述问题的自动化复现、测试、验证框架。 使用本框架解决问题的思路如下：

![](./readme1.png)


<br/>
<br/>
<br/>

# 本框架支持的feature
1. 使用python语言编写
2. 支持读取串口输入
3. 支持向串口写入命令
4. 支持本机执行测试命令
5. 支持向微信、飞书等发送消息
6. 支持远程控制小米插座，以控制单板重启（需要安装Home assistant）
7. 所有log支持本地保存，方便排查记录


<br/>
<br/>

# 使用示例
参考 main.py 中的main函数：
```python
def main():
    # 开始测试前重启一次
    before_test()

    # 主入口
    count = 1
    maxcount=10000
    while count < maxcount:
        logging.info("测试次数 {}/{}".format(count, maxcount))
        count+=1
        ret = do_test()
        if ret==True:
            #再次测试
            continue
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
```

你需要自己实现 before_test() 函数，以及 do_test()函数，如果 do_test()函数返回False，程序会认为测试失败，发送飞书消息（需要替换为你自己的飞书消息链接）

目前已经提供了一些功能函数可供直接使用：
### 串口收发：
```python
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
```

### 操作小米插座：

```python

def check_switch_state():
    url = base_url + "/api/states/" + entity_id
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxNmI0YTk5YjUwNTI0Y2Y5OWU5YjY1YjVhYjhhOWQwYiIsImlhdCI6MTcyOTQ5OTAxOSwiZXhwIjoyMDQ0ODU5MDE5fQ.CWhh71Tu9AdIYw5REwvwNe4w7dmpgLFXFo0ANPOP0LI",
        "content-type": "application/json",
    }

    response = get(url, headers=headers)
    response = json.loads(response.text)
    logging.info("获取插座状态成功，状态：{}".format(response["state"]))
    if response["state"] == "on" :
        state = OPERATE.ON
    elif response["state"] == "off" :
        state = OPERATE.OFF
    else:
        raise Exception("获取插座状态失败") 

    return state


def switch_operate(op:OPERATE):
    # state = check_switch_state()

    # if(op == state):
    #     logging.warning("插座状态已经是{}".format(op.name))



    logging.info("准备设置插座状态为：{}".format(op.name))
    target_stat = "turn_on" if op == OPERATE.ON else "turn_off"
    action = "/switch/{}".format(target_stat)
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxNmI0YTk5YjUwNTI0Y2Y5OWU5YjY1YjVhYjhhOWQwYiIsImlhdCI6MTcyOTQ5OTAxOSwiZXhwIjoyMDQ0ODU5MDE5fQ.CWhh71Tu9AdIYw5REwvwNe4w7dmpgLFXFo0ANPOP0LI",
    }
    data = {"entity_id": entity_id}
    url = base_url + "/api/services" + action
    response = post(url, headers=headers, json=data)
    logging.info(response.text)
​​​
Shift + Enter 换行

```