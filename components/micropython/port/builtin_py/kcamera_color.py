import sensor,image,lcd,time
import KPU as kpu
import gc, sys
import math

# ai_color|circle|color
THRESHOLD = 50
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_CYAN = (0, 255, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_PIRPLE = (255, 0, 255)

COLORS = [COLOR_WHITE, COLOR_BLACK, COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_PIRPLE]
COLOR_TAGS = ['white', 'black', 'red', 'green', 'blue', 'cyan', 'yellow', 'pirple']
class ColorUtils():
    name = 'color'
    def __init__(self):
        # 默认ROI为中间20x20的区域
        self.roi = (150, 110, 20, 20)
        self.result = {
            'color': None,  # 颜色预判数值
            'rgb': None     # RGB数值
        }
        
    def GetLAB(self, img):
        statistics = img.get_statistics(roi = self.roi)
        color_lab = (statistics.l_mode(), statistics.a_mode(), statistics.b_mode())
        # 返回LAB数值
        return color_lab

    def GetRGB(self, img):
        # LAB转换为RGB色域
        lab = self.GetLAB(img)
        rgb = image.lab_to_rgb(lab)

        # 画取色框
        img.draw_rectangle(self.roi, color=(228,247,70))
        img.draw_rectangle(0, 210, 320, 30, color=rgb, thickness=1, fill=True)
        # title = str(rgb).encode('utf-8')
        title = ('(%d,%d,%d)' % (rgb[0], rgb[1], rgb[2])).encode('utf-8')
        img.draw_string((320 - len(title) * 16) // 2, 217, title, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
        return rgb

    # def CheckColor(self, img, rgb=None):
    #     img = sensor.snapshot()
    #     if rgb == None:
    #         rgb = self.GetRGB(img)
    #     red = rgb[0]  #判断第一个r
    #     green = rgb[1]
    #     blue = rgb[2]
    #     color_s = ''
    #     if red < THRESHOLD:    #往黑走
    #         if green < THRESHOLD: #黑走
    #             if blue < THRESHOLD: #黑走
    #                 color_s = 'black'
    #             else :      # 蓝
    #                 color_s = 'blue'
    #         else:               # 往绿走
    #             if blue < THRESHOLD :                
    #                 color_s = 'green'
    #             else:
    #                 color_s= 'Cyan'
    #     else:               #往白走
    #         if green < THRESHOLD :  #  
    #             if blue < THRESHOLD :
    #                 color_s ='red'
    #             else:
    #                 color_s ='pirple'
    #         else :
    #             if blue < THRESHOLD:
    #                 color_s = 'yellow'
    #             else :
    #                 color_s = 'white'

    #     self.result = str(color_s).encode('utf-8')
    #     return self.result

    def VectorLen(self, vec_a, vec_b):
        vec = [0, 0, 0]
        for axis in range(len(vec_a)):
            vec[axis] = vec_a[axis] - vec_b[axis]

        # now vec is [x, y, z]
        # Calc Len
        return math.sqrt(vec[0]*vec[0] + vec[1]*vec[1] + vec[2]*vec[2])

    def CheckColor(self, rgb=None):
        img = sensor.snapshot()
        if rgb == None:
            rgb = self.GetRGB(img)
        
        color = 255
        index = 0
        if len(rgb) == 3:  
            for color_index in range(len(COLORS)):
                d_color = self.VectorLen(rgb, COLORS[color_index])
                # 找出最相似的颜色
                if d_color < color:
                    color = d_color
                    index = color_index

        # self.result = COLOR_TAGS[index].encode('utf-8')
        self.result['color'] = COLOR_TAGS[index]
        self.result['rgb'] = rgb

        # str_print = ('(%d,%d,%d)' % (rgb[0], rgb[1], rgb[2])).encode('utf-8')

        # 右下角画结果
        str_print = self.result['color'].encode('utf-8')
        len_str = len(str_print) * 16
        img.draw_rectangle(320 - len_str - 20, 180, len_str + 20, 30, color=(255,128,0), thickness=1, fill=True)
        img.draw_string(320 - len_str - 5, 187, str_print, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
        return img


    def GetColor(self, img, rgb=None):
        if rgb == None:
            rgb = self.GetRGB(img)
        
        color = 255
        index = 0
        if len(rgb) == 3:  
            for color_index in range(len(COLORS)):
                d_color = self.VectorLen(rgb, COLORS[color_index])
                # 找出最相似的颜色
                if d_color < color:
                    color = d_color
                    index = color_index

        # self.result = COLOR_TAGS[index].encode('utf-8')
        # self.result['color'] = COLOR_TAGS[index]
        # self.result['rgb'] = rgb

        # str_print = ('(%d,%d,%d)' % (rgb[0], rgb[1], rgb[2])).encode('utf-8')

        # 右下角画结果
        # str_print = self.result['color'].encode('utf-8')
        # len_str = len(str_print) * 16
        # img.draw_rectangle(320 - len_str - 20, 180, len_str + 20, 30, color=(255,128,0), thickness=1, fill=True)
        # img.draw_string(320 - len_str - 5, 187, str_print, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
        return COLOR_TAGS[index]

    def __deinit__(self):
        import gc
        gc.collect()

class ai_color_shape():
    def __init__(self):
        sensor.set_windowing((224, 224))
        self.model_addr=0x900000
        self.labels=["circle", "rectangle", "square", "triangle"]  # 形状识别种类
        self.anchors = [4.0, 4.34375, 4.46875, 4.65625, 4.125, 4.0625, 3.28125, 5.1875, 3.96875, 4.0]
        self.task = kpu.load(self.model_addr)
        kpu.init_yolo2(self.task, 0.5, 0.3, 5, self.anchors)

    def use_ai_color(self):
        img = sensor.snapshot()
        t = time.ticks_ms()
        objects = kpu.run_yolo2(self.task, img)
        t = time.ticks_ms() - t
        if objects:
            for obj in objects:
                pos = obj.rect()
                img.draw_rectangle(pos)
                img.draw_string(pos[0], pos[1], "%s : %.2f" %(self.labels[obj.classid()], obj.value()), scale=2, color=(255, 0, 0))
        img.draw_string(0, 200, "t:%dms" %(t), scale=2, color=(255, 0, 0))
        lcd.display(img)

    def __deinit__(self):
        kpu.deinit(self.task)
        del self.task
        self.task = None
        gc.collect()


                


        


            


        
        

