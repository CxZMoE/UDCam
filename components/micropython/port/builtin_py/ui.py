from micropython import const
from Maix import FPIOA, GPIO
from fpioa_manager import fm
import time

SCREEN_WIDTH = const(320)
SCREEN_HEIGHT = const(240)

LANG_ZH = const(0x0)
LANG_EN = const(0x1)
lang = LANG_ZH

fm.register(35, fm.fpioa.GPIOHS8)
fm.register(28, fm.fpioa.GPIOHS5)
right_key=GPIO(GPIO.GPIOHS8,GPIO.IN, GPIO.PULL_UP)
left_key = GPIO(GPIO.GPIOHS5,GPIO.IN, GPIO.PULL_UP)

# 补光灯按键
from modules import ws2812
class_ws2812 = ws2812(32,4)
class_ws2812.set_led(0,(0x00,0x00,0x00))
class_ws2812.set_led(1,(0x00,0x00,0x00))
class_ws2812.set_led(2,(0x00,0x00,0x00))
class_ws2812.set_led(3,(0x00,0x00,0x00))
class_ws2812.display()
class MUI():
    def __init__(self):
        self.title = 'K210摄像头'
        self.menuItems = []
        self.showMenu = False
        self.menuItemSelected = 0
        self.led_on = False
        # 菜单页数
        self.menuPage = 0

    def setTitle(self, title):
        self.title = title
    
    def drawMenuBar(self, img):
        img.draw_rectangle(0, 0, 320, 30, color=(255,128,0), thickness=1, fill=True)
        title = GetIntl(self.title)
        title_x = (SCREEN_WIDTH - GetStrLenFixed(title)) // 2
        # 画标题
        DrawString(img, title_x, 7, title)
        # 画箭头
        img.draw_arrow(20, 15, 10, 15)
        img.draw_arrow(SCREEN_WIDTH - 20, 15, SCREEN_WIDTH - 10, 15)

    def drawCursor(self, img):
        img.draw_cross(320//2, 240//2, color=(255,128,0),size=10)

    def GetLeftPressed(self):
        if (left_key.value() == 0):
            while (left_key.value() != 1):
                pass
            return True
        return False
    def GetRightPressed(self):
        t = time.ticks_ms()
        if (right_key.value() == 0):
            while (right_key.value() != 1):
                if time.ticks_ms() - t > 2000:
                    if self.led_on:
                        for i in range(4):
                            class_ws2812.set_led(i,(0x00,0x00,0x00))
                    else:
                        for i in range(4):
                            class_ws2812.set_led(i,(0xff,0xff,0xff))
                    self.led_on = ~self.led_on
                    class_ws2812.display()
                    t = time.ticks_ms()
                pass
            return True
        return False

    def DrawMenu(self, img):
        if (not self.showMenu):
            return
        # 画菜单外框
        marginTop = 30
        width = 180
        height = SCREEN_HEIGHT - marginTop
        img.draw_rectangle(0, marginTop, width, height, color=(255,128,0), thickness=1, fill=True)

        item_width = 180
        item_height = 30
        items = self.menuItems
        # 更新菜单列表
        menu_length = len(items)
        if (menu_length > 0):
            self.menuPage = self.menuItemSelected // 7
            page_start = self.menuPage * 7
            page_end = self.menuPage * 7 + 7
            if page_end > menu_length:
                page_end = menu_length
            for index in range(page_start, page_end):
                item = items[index][0](items[index][1])
                item_y = marginTop + (index - page_start)*item_height
                if (index == self.menuItemSelected):
                    img.draw_rectangle(0, item_y, item_width, item_height, color=(255,50,0), thickness=1, fill=True)
                else:
                    img.draw_rectangle(0, item_y, item_width, item_height, color=(255,110,0), thickness=1, fill=True)
                img.draw_line(0, item_y, item_width - 1, item_y, color=(255,255,255), thickness=1)
                DrawString(img, (item_width - GetStrLenFixed(item)) // 2, item_y + 7, item)


    def AddMenuItem(self, item, arg):
        if (len(arg) > 0):
            self.menuItems.append([item, arg])
    def DelMenuItem(self, item, arg):
        try:
            self.menuItems.remove([item, arg])
        except:
            pass

def DrawString(img, x, y, str, color=(255,255,255)):
    x += 8
    for c in str:
        if ord(c) < 128:
            img.draw_string(x, y, c, color=color, scale=1)
            x += 8
        else:
            img.draw_string(x, y, c, color=color, scale=1)
            x += 16
# Msg库

Msgs = {
    "K210摄像头": {
        "en": "K210-CAM"
    },
    "物体识别": {
        "en": "Object Recognition"
    },
    "分类识别": {
        "en": "Classifier"
    },
    "人脸识别": {
        "en": "Face Detection"
    },
    "二维码识别": {
        "en": "QRCode"
    },
    "条形码识别": {
        "en": "BarCode"
    },
    "颜色识别": {
        "en": "Color Detection"
    },
    "循迹识别": {
        "en": "Route Detection"
    },
    "标签识别": {
        "en": "Tag Detection"
    },
    "版本: 1.0.0": {
        "en": "Ver: 1.0.0"
    },
    "切换语言": {
        "en": "Change Language"
    }
}

# 使用UTF-8编码
for key in Msgs.keys():
    Msgs[key]['en'] = Msgs[key]['en']
    Msgs[key]['zh'] = key

# 获取国际化字段
def GetIntl(msg):
    if lang == LANG_ZH:
        return Msgs[msg]['zh']
    elif lang == LANG_EN:
        return Msgs[msg]['en']

def GetStrLength(msg):
    return len(msg.decode()) * 16

def GetStrLenFixed(msg):
    len = 0
    for c in msg:
        if ord(c) < 128:
            len += 8
        else:
            len += 16
    # print('len(%s): %d' % (msg, len))
    return len
