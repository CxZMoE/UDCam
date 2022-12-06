from micropython import const
import machine
from machine import I2C
import time
import gc
import ui
# I2C 传输标识
I2C_TRANS_START = const(0x00)
I2C_TRANS_END   = const(0x02)
DATA_SEPERATOR = '|'

# 运行模式
KC_MODE_NONE = 'none'                      # 无
KC_MODE_OBJ = 'obj'                        # 物体识别
KC_MODE_HUMAN_FACE = 'face'                # 人脸识别
KC_MODE_SELF_LEARNING = 'self_learning'    # 自学习分类
KC_MODE_QRCODE = 'qrcode'                  # 二维码识别
KC_MODE_BARCODE = 'barcode'                # 条形码识别
KC_MODE_COLOR = 'color'                    # 颜色识别
KC_MODE_ROUTE = 'route'                    # 循迹识别
KC_ACT_START =  'start'                    # 开始
KC_ACT_STOP =   'stop'                     # 停止
KC_ACT_SWITCH = 'switch'                   # 切换
KC_ACT_GET = 'get'                         # 获取

# 运行状态
KC_MODE_STATUS_RUNNING = const(0x00)
KC_MODE_STATUS_STOPPED = const(0x01)


# 运行状态和模式
currentMode = KC_MODE_NONE # 空状态
currentItem = None # 当前模式的对象
process_callback = None
timeout = 50

# I2C数据缓冲区
from ringbuf import RINGBUFFER
i2cRxBuffer = RINGBUFFER(4096)  # I2C 发送环形缓冲区
i2cTxBuffer = b''               # I2C 发送缓存
i2cTxEnd = False                # I2C 是否发送结束
i2cTxIndex = 0                  # I2C 发送序号


# I2C的回调函数
def on_receive(c):
    i2cRxBuffer.put(c)

def on_event(event):
    # 当I2C传输时间发生时
    if event == I2C_TRANS_START:
        pass
    if event == I2C_TRANS_END:
        global i2cTxIndex , i2cRxIndex, queue
        i2cTxIndex = 0

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

import json
def gen_payload(data):
    data = {
        'mode': currentMode,
        'payload': data
    }

    return json.dumps(data).encode('utf-8')

## 初始化I2C ##
i2c = I2C(I2C.I2C0, mode=I2C.MODE_SLAVE, scl=11, sda=12, freq=400000, addr=77,addr_size=7, 
    on_receive=on_receive, on_transmit=on_transmit, on_event=on_event)


## 初始化镜头 ##
import sensor
sensor.reset()
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.RGB565)
sensor.set_hmirror(0)
sensor.set_vflip(1)
sensor.run(1)
print('[KC] 摄像头初始化完毕')

## 初始化LCD屏幕 [320X240] ##
import lcd, image
lcd.init()
lcd.rotation(0)
image.font_load(image.UTF8, 16, 16, 0xA00000)
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


# check IDE mode
ide = False
if (boot_key.value() == 0):
    ide =True

if ide:
    print('[KC] 进入IDE模式')
    import sys
    from machine import UART
    import lcd
    lcd.init(color=lcd.PINK)
    repl = UART.repl_uart()
    repl.init(1500000, 8, None, 1, read_buf_len=2048, ide=True, from_ide=False)
    sys.exit()
del ide

## UI ##
from ui import MUI
mui = MUI()
# mui.AddMenuItem('Object Recognition')
# mui.AddMenuItem('Classifier')
# mui.AddMenuItem('Face Detection')
# mui.AddMenuItem('Binary Code')
mui.AddMenuItem('物体识别'.encode('utf-8'))
mui.AddMenuItem('分类识别'.encode('utf-8'))
mui.AddMenuItem('人脸识别'.encode('utf-8'))
mui.AddMenuItem('二维码识别'.encode('utf-8'))
mui.AddMenuItem('条形码识别'.encode('utf-8'))
mui.AddMenuItem('颜色识别'.encode('utf-8'))
mui.AddMenuItem('循迹识别'.encode('utf-8'))

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

def switch_mode(mode):
    global currentItem
    global currentMode
    global process_callback
    # 开始学习模式
    if (mode == mui.menuItems[0]):
        import kcamera_objrec as mode
        # 开始物体识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_OBJ)):
            clearItem()
            currentItem = mode.KCamera_ObjectRec()
            currentMode = KC_MODE_OBJ
        process_callback = currentItem.process
        mui.setTitle('物体识别'.encode('utf-8'))
    elif (mode == mui.menuItems[1]):
        import kcamera_selflearning as mode
        # 开始分类识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_SELF_LEARNING)):
            clearItem()
            currentItem = mode.KCameraSelfLearning(4, boot_key)
            currentMode = KC_MODE_SELF_LEARNING
        process_callback = currentItem.star_learn
        mui.setTitle('分类识别'.encode('utf-8'))
    elif (mode == mui.menuItems[2]):
        import kcamera_face as mode
        # 开始人脸识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_HUMAN_FACE)):
            clearItem()
            currentItem = mode.KCamera_Face()
            currentMode = KC_MODE_HUMAN_FACE
            process_callback = currentItem.Fr
            mui.setTitle('人脸识别'.encode('utf-8'))
    elif (mode == mui.menuItems[3]):
        import kcamera_qrcode as mode
        # 开始二维码识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_QRCODE)):
            clearItem()
            currentItem = mode.KCameraQRCode()
            currentMode = KC_MODE_QRCODE
        process_callback = currentItem.QrCode
        mui.setTitle('二维码识别'.encode('utf-8'))
    elif (mode == mui.menuItems[4]):
        import kcamera_qrcode as mode
        # 开始条形码识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_BARCODE)):
            clearItem()
            currentItem = mode.KCameraQRCode()
            currentMode = KC_MODE_QRCODE
        process_callback = currentItem.BarCode
        mui.setTitle('条形码识别'.encode('utf-8'))
    elif (mode == mui.menuItems[5]):
        import kcamera_color as mode
        # 开始颜色识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_COLOR)):
            clearItem()
            currentItem = mode.ColorUtils()
            currentMode = KC_MODE_COLOR
        process_callback = currentItem.CheckColor
        mui.setTitle('颜色识别'.encode('utf-8'))
    elif (mode == mui.menuItems[6]):
        import kcamera_route as mode
        # 开始循迹识别
        if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_ROUTE)):
            clearItem()
            currentItem = mode.FindRouteBlobs()
            currentMode = KC_MODE_ROUTE
        process_callback = currentItem.Process
        mui.setTitle('循迹识别'.encode('utf-8'))



# 执行回调
while True:
    # 进行数据解析
    read = b''
    t = time.ticks_ms()
    # 超时时间
    while time.ticks_ms() - t < timeout:
        c = i2cRxBuffer.get()
        if (c != None):
            if (c == 0x03):
                break
            read += chr(c)
    # 解析并且使用分隔符切分
    i2cRxParsed = read.decode().split(DATA_SEPERATOR)
    # 处理逻辑
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
                    currentMode = KC_MODE_SELF_LEARNING
                process_callback = currentItem.star_learn
                mui.setTitle('分类模式'.encode('utf-8'))
            elif (i2cRxParsed[1] == mode.KC_ACT_LOADMODE):
                # 开始加载分类器模式
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_SELF_LEARNING)):
                    clearItem()
                    currentItem = mode.KCameraSelfLearning(4, boot_key)
                    currentMode = KC_MODE_SELF_LEARNING
                if (len(i2cRxParsed) >= 3):
                    print('[KC] 加载自学习分类器: {}'.format(i2cRxParsed[2]))
                    currentItem.load_save_learn(str(i2cRxParsed[2]) + '.classifier')
                    process_callback = currentItem.load_self_learning_mode
                    # mui.setTitle('Classifier Mode[%s]' % (str(i2cRxParsed[2]) + '.classifier'))
                    mui.setTitle(('分类模式: %s' % (str(i2cRxParsed[2]))).encode('utf-8'))
                else:
                    print('[KC] 加载分类器失败: 参数不全')
            elif (i2cRxParsed[1] == mode.ACT_UPDATE_SAVE_NAME):
                # 更新分类器名称
                if (len(i2cRxParsed) >= 3):
                    currentItem.load_classifier()
                    currentItem.update_save_name(i2cRxParsed[2] + '.classifier')
                    print('[KC] 更新分类器名称: {}'.format(i2cRxParsed[2]))
                else:
                    print('[KC] 更新分类器名称失败: 参数不全')
            elif (i2cRxParsed[1] == mode.ACT_GET):
                # 获取识别结果
                i2cTxBuffer = gen_payload(currentItem.result)
                
                print('[KC] 用户进行数据请求...')
        elif (i2cRxParsed[0] == KC_MODE_OBJ):
            # 物体识别
            import kcamera_objrec as mode
            if (i2cRxParsed[1] == KC_ACT_START):
                # 开始物体识别
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_OBJ)):
                    clearItem()
                    currentItem = mode.KCamera_ObjectRec()
                    currentMode = KC_MODE_OBJ
                process_callback = currentItem.process
                mui.setTitle('物体识别'.encode('utf-8'))
            elif (i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                i2cTxBuffer = gen_payload(currentItem.result)
        elif (i2cRxParsed[0]) == KC_MODE_HUMAN_FACE:
            # 人脸识别
            import kcamera_face as mode
            if (i2cRxParsed[1] == KC_ACT_START):
                # 开始人脸识别
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_HUMAN_FACE)):
                    clearItem()
                    currentItem = mode.KCamera_Face()
                    currentMode = KC_MODE_HUMAN_FACE
                    process_callback = currentItem.Fr
                    mui.setTitle('人脸识别'.encode('utf-8'))
            elif (i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                print('[KC] 用户进行数据请求...')
                i2cTxBuffer = gen_payload(currentItem.result)
            elif (i2cRxParsed[1] == 'add'):
                # 添加保存的人脸
                if (len(i2cRxParsed) > 2):
                    currentItem.AddFace(i2cRxParsed[2])
                else:
                    print('[KC] 人脸名称错误')
            elif (i2cRxParsed[1] == 'del'):
                # 删除人脸
                if (len(i2cRxParsed) > 2):
                    if (i2cRxParsed[2] == 'all'):
                        # 删除全部
                        currentItem.DelAllFace()
                    else:
                        currentItem.DelFace(i2cRxParsed[2])
                else:
                    print('[KC] 人脸名称错误')
        elif (i2cRxParsed[0]) == KC_MODE_QRCODE:
            if (i2cRxParsed[1] == KC_ACT_START):
                import kcamera_qrcode as mode
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_QRCODE)):
                    # 开始人脸识别
                    clearItem()
                    currentItem = mode.KCameraQRCode()
                    currentMode = KC_MODE_QRCODE
                    process_callback = currentItem.QrCode
                    mui.setTitle('二维码识别'.encode('utf-8'))
            elif (i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                print('[KC] 用户进行数据请求...')
                i2cTxBuffer = gen_payload(currentItem.result)
        elif (i2cRxParsed[0]) == KC_MODE_BARCODE:
            if (i2cRxParsed[1] == KC_ACT_START):
                import kcamera_qrcode as mode
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_QRCODE)):
                    # 开始人脸识别
                    clearItem()
                    currentItem = mode.KCameraQRCode()
                    currentMode = KC_MODE_QRCODE
                    process_callback = currentItem.QrCode
                    mui.setTitle('条形码识别'.encode('utf-8'))
            elif (i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                print('[KC] 用户进行数据请求...')
                i2cTxBuffer = gen_payload(currentItem.result)

        elif(i2cRxParsed[0] == KC_MODE_COLOR):
            if (i2cRxParsed[1] == KC_ACT_START):
                import kcamera_color as mode
                # 开始人脸识别
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_COLOR)):
                    clearItem()
                    currentItem = mode.ColorUtils()
                    currentMode = KC_MODE_COLOR
                process_callback = currentItem.CheckColor
                mui.setTitle('颜色识别'.encode('utf-8'))
            elif (i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                print('[KC] 用户进行数据请求...')
                i2cTxBuffer = gen_payload(currentItem.result)
        elif(i2cRxParsed[0] == KC_MODE_ROUTE):
            if (i2cRxParsed[1] == KC_ACT_START):
                import kcamera_route as mode
                # 开始循迹识别
                if (currentItem == None or (currentItem != None and currentItem.name != KC_MODE_ROUTE)):
                    clearItem()
                    currentItem = mode.FindRouteBlobs()
                    currentMode = KC_MODE_ROUTE
                process_callback = currentItem.Process
                mui.setTitle('循迹识别'.encode('utf-8'))
            elif(i2cRxParsed[1] == KC_ACT_GET):
                # 获取识别结果
                print('[KC] 用户进行数据请求...')
                i2cTxBuffer = gen_payload(currentItem.result)

    if (process_callback != None):
        img = process_callback()
    else:
        # 没有选择模式的时候直接显示摄像头画面
        sensor.set_windowing((320, 240))
        img = sensor.snapshot()
        # img = img.draw_string(0, 200, b'Underdog工作室', color=lcd.GREEN,scale=1)
        
    if (img != None):
        # 菜单栏
        mui.drawMenuBar(img)
        # 光标
        mui.drawCursor(img)
        # 菜单
        mui.DrawMenu(img)
        lcd.display(img)
    
    if (mui.GetRightPressed()):
        if (mui.showMenu):
            # 菜单模式
            if (mui.menuItemSelected < len(mui.menuItems) - 1):
                mui.menuItemSelected += 1
            else:
                mui.menuItemSelected = 0
    elif (mui.GetLeftPressed()):
        mui.showMenu = not mui.showMenu
        if (not mui.showMenu):
            switch_mode(mui.menuItems[mui.menuItemSelected])
        

    print(time.ticks_ms() / 1000)
machine.reset()
