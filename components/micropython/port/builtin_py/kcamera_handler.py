# 该文件定义了当作为I2C从机设备接收到数据以后的处理
import sensor,lcd
from micropython import const
from Maix import FPIOA, GPIO
import gc

import kcamera_i2c
import kcamera_objrec
import kcamera_selflearning
import time
# 这里定义一些执行的操作(ACT)
# (ACT): 示意处理器进行操作
KC_ACT_START =  const(0x00)     # 开始执行操作
KC_ACT_STOP =   const(0x01)     # 停止当前操作
KC_ACT_SWITCH = const(0x02)     # 切换当前操作到另一个操作

# (ACT_ITEM): 操作的目标，如图像处理、人脸识别、物体识别
KC_ACTI_NONE = const(0x00)
KC_ACTI_OBJ = const(0x01)
KC_ACTI_HUMAN_FACE = const(0x02)
KC_ACTI_SELF_LEARNING = const(0x03)

# 定义一些参数
KC_ARG_ACT = const(0x00)    # 当前的操作
KC_ARG_DATA = const(0x01)   # 当前操作附带的数据（如果存在的话）

class KCameraHandler():
    def __init__(self):
        # 初始化传感器和屏幕
        sensor.reset()
        sensor.set_framesize(sensor.QVGA)
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_hmirror(0)
        sensor.set_vflip(1)
        sensor.run(1)
        print('[SENSOR] Initialized')
        lcd.init()
        lcd.rotation(0)
        print('[LCD] Initialized')
        fpioa = FPIOA()
        # 补光灯按键
        fpioa.set_function(26,FPIOA.GPIOHS7)
        self.led_b = GPIO(GPIO.GPIOHS7,GPIO.OUT)
        # 某个按键（未确定）
        fpioa.set_function(25,FPIOA.GPIOHS6)
        self.key = GPIO(GPIO.GPIOHS6,GPIO.IN)
        print('[KEY] Initialized')
    
    # 发送数据
    def on_transmit(self):
        data = self.transmit_buffer
        if self.transmit_count > len(data) - 1:
            return 0x0a
        if data[self.transmit_count] != None:
            c = self.transmit_buffer[self.transmit_count]
            self.transmit_count += 1
            return c
        else:
            self.transmit_count = 0