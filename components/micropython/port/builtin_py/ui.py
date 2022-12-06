from micropython import const
from Maix import FPIOA, GPIO
from fpioa_manager import fm
import time

SCREEN_WIDTH = const(320)
SCREEN_HEIGHT = const(240)

fm.register(16, fm.fpioa.GPIOHS8)
right_key=GPIO(GPIO.GPIOHS8,GPIO.PULL_UP)
fm.fpioa.set_function(25,FPIOA.GPIOHS6)
left_key = GPIO(GPIO.GPIOHS6,GPIO.IN)

class MUI():
    def __init__(self):
        self.title = 'K210摄像头'.encode('utf-8')
        self.menuItems = []
        self.showMenu = False
        self.menuItemSelected = 0
    def setTitle(self, title):
        self.title = title
    def drawMenuBar(self, img):
        img.draw_rectangle(0, 0, 320, 30, color=(255,128,0), thickness=1, fill=True)
        title_len = len(self.title.decode()) * 16 # 标题的长度(像素)
        title_x = (SCREEN_WIDTH - title_len) // 2
        # 画标题
        img.draw_string(title_x, 7, self.title, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
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
        if (right_key.value() == 0):
            while (right_key.value() != 1):
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
        if (len(items) > 0):
            for item in items:
                item_y = marginTop + items.index(item)*item_height
                if (items.index(item) == self.menuItemSelected):
                    img.draw_rectangle(0, item_y, item_width, item_height, color=(255,50,0), thickness=1, fill=True)
                else:
                    img.draw_rectangle(0, item_y, item_width, item_height, color=(255,110,0), thickness=1, fill=True)
                img.draw_line(0, item_y, item_width - 1, item_y, color=(255,255,255), thickness=1)
                img.draw_string((item_width - (len(item.decode()) * 16)) // 2, item_y + 7, item, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)

    def AddMenuItem(self, item):
        if (len(item) > 0):
            self.menuItems.append(item)
    def DelMenuItem(self, item):
        try:
            self.menuItems.remove(item)
        except:
            pass

                


        

