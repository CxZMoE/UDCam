import sensor,lcd
from micropython import const
import machine
from machine import I2C
import time
import gc

# I2C 传输标识
I2C_TRANS_START = const(0x00)
I2C_TRANS_END   = const(0x02)

# 运行模式
KC_MODE_NONE = 'none'                      # 无
KC_MODE_OBJ = 'obj'                        # 物体识别
KC_MODE_HUMAN_FACE = 'face'                # 人脸识别
KC_MODE_SELF_LEARNING = 'self_learning'    # 自学习分类

KC_ACT_START =  'start'                    # 开始
KC_ACT_STOP =   'stop'                     # 停止
KC_ACT_SWITCH = 'switch'                   # 切换
KC_ACT_GET = 'get'                         # 获取

# 运行状态
KC_MODE_STATUS_RUNNING = const(0x00)
KC_MODE_STATUS_STOPPED = const(0x01)

# 运行状态和模式
currentMode = KC_MODE_NONE # 空状态
currentModeStatus = KC_MODE_STATUS_STOPPED # 已停止
currentItem = None # 当前模式的对象
currentModeData = []
# I2C数据缓冲区
i2cRxParsed = []
i2cRxBuffer = bytearray(128)
i2cRxIndex = 0

i2cTxBuffer = b''       # I2C 发送缓存
i2cTxEnd = False        # I2C 是否发送结束
i2cTxIndex = 0          # I2C 发送序号

queue = []


# I2C的回调函数
def on_receive(c):
    global i2cRxBuffer,i2cRxIndex
    i2cRxBuffer[i2cRxIndex] = c
    i2cRxIndex = i2cRxIndex + 1

def on_event(event):
    # 当I2C传输时间发生时
    if event == I2C_TRANS_START:
        pass
    if event == I2C_TRANS_END:
        global i2cTxIndex , i2cRxIndex, queue
        i2cTxIndex = 0
        t = i2cRxBuffer[:i2cRxIndex].decode().split('|')
        if (len(t) > 1 and len(queue) < 5):
            i2cRxParsed = t
            queue.append(i2cRxParsed)
            print(i2cRxParsed) # 打印接收到的数据
        i2cRxIndex = 0
        del t

def on_transmit():
    global i2cTxIndex
    # 当Master使用Read函数的时候
    # print('[KC] Tx Buffer: {}'.format(i2cTxBuffer))
    # print('[KC] Tx Buffer len: {}'.format(len(i2cTxBuffer)))
    if (i2cTxIndex < len(i2cTxBuffer)):
        i2cTxIndex = i2cTxIndex + 1
        # print('[KC] Send With Index: %d' % (i2cTxIndex - 1))
        # print('[KC] Send: {}'.format(i2cTxBuffer[i2cTxIndex - 1]))
        return i2cTxBuffer[i2cTxIndex - 1]
    return 0x0a
## 初始化I2C ##
i2c = I2C(I2C.I2C0, mode=I2C.MODE_SLAVE, scl=11, sda=12, freq=400000, addr=77,addr_size=7, 
    on_receive=on_receive, on_transmit=on_transmit, on_event=on_event)

## 初始化镜头 ##
sensor.reset()
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.RGB565)
sensor.set_hmirror(0)
sensor.set_vflip(1)
sensor.run(1)
print('[KC] 摄像头初始化完毕')

## 初始化LCD屏幕 [320X240] ##
lcd.init()
lcd.rotation(0)
print('[KC] 屏幕初始化完毕')

## 初始化按键 ##
from Maix import FPIOA, GPIO
fpioa = FPIOA()
# 补光灯按键
fpioa.set_function(26,FPIOA.GPIOHS7)
led_key = GPIO(GPIO.GPIOHS7,GPIO.OUT)
# BOOT按键
fpioa.set_function(25,FPIOA.GPIOHS6)
boot_key = GPIO(GPIO.GPIOHS6,GPIO.IN)

print('[KC] 按键初始化完毕')

# 主循环
def clearItem():
    global currentItem
    if (currentItem != None):
        print('[KC] 清除残留模型')
        currentItem.__deinit__() # 解构
        currentItem = None
def initItem(obj):
    global currentItem
    currentItem = obj

# 执行回调
func = None

while True:
    # 进行数据解析
    if (len(queue) > 0):
        i2cRxParsed = queue[0]
        if (len(i2cRxParsed) >= 2):
            # 至少是 ['obj','start']
            if (i2cRxParsed[0] == KC_MODE_SELF_LEARNING):
                # 自学习分类
                import kcamera_selflearning as mode
                if (i2cRxParsed[1] == KC_ACT_START):
                    # 开始学习模式
                    if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_SELF_LEARNING)):
                        clearItem()
                        currentItem = mode.KCameraSelfLearning(4, boot_key)
                    func = currentItem.star_learn
                elif (i2cRxParsed[1] == mode.KC_ACT_LOADMODE):
                    # 开始加载分类器模式
                    if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_SELF_LEARNING)):
                        clearItem()
                        currentItem = mode.KCameraSelfLearning(4, boot_key)
                    if (len(i2cRxParsed) >= 3):
                        print('[KC] 加载自学习分类器: {}'.format(i2cRxParsed[2]))
                        currentItem.load_save_learn(str(i2cRxParsed[2]))
                        func = currentItem.load_self_learning_mode
                    else:
                        print('[KC] 加载分类器失败: 参数不全')
                elif (i2cRxParsed[1] == mode.ACT_UPDATE_SAVE_NAME):
                    # 更新分类器名称
                    if (len(i2cRxParsed) >= 3):
                        currentItem.load_classifier()
                        currentItem.update_save_name(i2cRxParsed[2])
                        print('[KC] 更新分类器名称: {}'.format(i2cRxParsed[2]))
                    else:
                        print('[KC] 更新分类器名称失败: 参数不全')
                elif (i2cRxParsed[1] == mode.ACT_GET):
                    # 获取识别结果
                    i2cTxBuffer = currentItem.result
                    print('[KC] 用户进行数据请求...')
            elif (i2cRxParsed[0] == KC_MODE_OBJ):
                # 物体识别
                import kcamera_face as mode
                if (i2cRxParsed[1] == KC_ACT_START):
                    # 开始物体识别
                    if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_SELF_LEARNING)):
                        clearItem()
                        currentItem = mode.KCamera_ObjectRec()
                    func = currentItem.process
                elif (i2cRxParsed[1] == KC_ACT_GET):
                    # 获取识别结果
                    i2cTxBuffer = currentItem.result
            
        queue = queue[1:]
    
    if (func != None):
        func()
        # gc.collect()
    else:
        # 没有选择模式的时候直接显示摄像头画面
        sensor.set_windowing((320, 240))
        img = sensor.snapshot()
        img = img.draw_string(0, 200, 'Underdog Studio', color=lcd.GREEN,scale=1)
        lcd.display(img)
    print(time.ticks_ms())
    time.sleep_ms(30)
machine.reset()
