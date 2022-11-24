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
KC_ACT_START =  b'start'     # 开始执行操作
KC_ACT_STOP =   b'stop'      # 停止当前操作
KC_ACT_SWITCH = b'switch'    # 切换当前操作到另一个操作

# (ACT_ITEM): 操作的目标，如图像处理、人脸识别、物体识别
KC_ACTI_NONE = const(0x00)
KC_ACTI_OBJ = const(0x01)
KC_ACTI_HUMAN_FACE = const(0x02)
KC_ACTI_SELF_LEARNING = const(0x03)

# 定义一些参数
KC_ARG_ACT = const(0x00)    # 当前的操作
KC_ARG_DATA = const(0x01)   # 当前操作附带的数据（如果存在的话）

class KCameraHandler():
    call = None
    cmd = b''
    mode = KC_ACTI_NONE
    transmit_buffer = b''
    transmit_count = 0
    transmit_flag = 0
    can_transmit = 0
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
        
    def kc_action_proxy(self):
        # Need When Stable: [try: except:]
        # 对数据进行解包
        data = kcamera_i2c.g_rbuf
        if kcamera_i2c.trans_end == 1 and len(data) > 0:
            data = data.lstrip(b'\x00')
            fun, args = self.parse_data(data)
            if fun.count(b'obj') > 0:
                if args[KC_ARG_ACT] == KC_ACT_START:
                    sensor.set_windowing((320, 240))
                    self.mode = KC_ACTI_OBJ
                    if self.call:
                        self.call.__deinit__()
                    self.call = kcamera_objrec.KCamera_ObjectRec()
                elif args[KC_ARG_ACT] == kcamera_objrec.ACT_GET:
                    self.clear_transmit_buffer()
            elif fun.count(b'self_learning') > 0:
                ## 开始自学习模式识别
                # 直接开始识别
                if self.mode != KC_ACTI_SELF_LEARNING:
                    print('修改模式为:', fun)
                    gc.collect()
                    if self.call:
                        self.call.__deinit__()
                    self.call = kcamera_selflearning.KCameraSelfLearning(4, self.key)
                    
                    self.mode = KC_ACTI_SELF_LEARNING
                if args[KC_ARG_ACT] == KC_ACT_START:
                    self.mode = KC_ACTI_SELF_LEARNING
                    #print('>> Start Self-Learning')
                    self.call.process = self.call.star_learn
                # 加载保存的分类器
                elif args[KC_ARG_ACT] == kcamera_selflearning.KC_ACT_LOADMODE:
                    self.mode = KC_ACTI_SELF_LEARNING
                    #print('>> Load Self-Learning')
                    #print(gc.mem_free())
                    if len(args) == 2:
                        #print('加载自学习文件:', args[KC_ARG_DATA])
                        saved_classifier = args[KC_ARG_DATA] + ".classifier"
                        if self.call.classifier:
                            self.call.classifier.__del__()
                        if(self.call.load_save_learn(saved_classifier.decode()) == 1):
                            print('加载成功')
                            self.call.process = self.call.load_self_learning_mode
                        else:
                            print('加载失败')
                            self.call.process = None
                # 更新保存的人脸名字
                elif args[KC_ARG_ACT] == kcamera_selflearning.ACT_UPDATE_SAVE_NAME:
                    if len(args) == 2:
                        name = args[KC_ARG_DATA]
                        self.mode = KC_ACTI_SELF_LEARNING
                        print('load classifier')
                        self.call.load_classifier()
                        print('load classifier end')
                        self.call.process = self.call.star_learn
                        self.call.update_save_name(name + ".classifier")
                # 获取保存的结果
                elif args[KC_ARG_ACT] == kcamera_selflearning.ACT_GET:
                    self.clear_transmit_buffer()
            # 清除grbuf
            kcamera_i2c.g_rbuf= b''

        if self.call and self.call.process:
            if self.transmit_flag != 1:
                self.call.process()

        print(gc.mem_free())

    # 发送处理结果
    def kc_send_result(self):
        raise NotImplementedError

    # 解析数据
    def parse_data(self, data):
        print('data')
        parsed = data.split(b'|')
        if not len(parsed) > 1:
            return b'',b''
        fun = parsed[0]
        args = parsed[1:]   # Tip: type of bytes, needs to be decoded before using it as string.
        return fun, args

    def async_sleep(self,ms):
        t = time.ticks_ms()
        while time.ticks_ms() - t <= ms:
            pass
        
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

    # 清除发送缓冲区
    def clear_transmit_buffer(self):
        if self.call != None and self.call.result != None:
            self.transmit_count = 0
            self.transmit_buffer = self.call.result