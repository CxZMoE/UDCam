import sensor,lcd
import KPU as kpu
import gc
from micropython import const
import time

 # 操作
ACT_GET = b'get'

#模型分类，按照 20class 顺序
#“飞机”、“自行车”、“鸟”、“船”、“瓶子”、“公交车”、“汽车”、“猫”、“椅子”、“牛”、“餐桌”、
#“狗”、“马”、“摩托车”、“人”、“土豆植物”、“羊”、“沙发”、“火车”、“电视监视器”

#初始化 yolo2 网络，识别可信概率为 0.5（50%）
class KCamera_ObjectRec():
    classes = ['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable', 'dog', 'horse', 'motorbike', 'person', 'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor']
    anchor = (1.08, 1.19, 3.42, 4.41, 6.63, 11.38, 9.42, 5.11, 16.62, 10.52)

    # KPU网络对象(kpu.init)
    kpu_net_obj = None

   

    # 识别结果
    result = ''
    def __init__(self):
        # 首先加载物体的模型(KModel)
        self.kpu_net_obj = kpu.load(0x600000)
        kpu.init_yolo2(self.kpu_net_obj, 0.5, 0.3, 5, self.anchor)
    
    # 对图像进行处理，物体识别
    def process(self):
        try:
            img = sensor.snapshot()
        except:
            return
        try:
            items = kpu.run_yolo2(self.kpu_net_obj, img)
            # 遍历识别结果的对象
            if items:
                for item in items:
                    x = item.x()
                    y = item.y()
                    id = item.classid()
                    # 为对象画框
                    img.draw_rectangle(item.rect())
                    img.draw_string(x+5, y, self.classes[id], color=lcd.ORANGE)
                
                # 为结果赋值
                self.result = self.classes[id].encode()
                # kcamera_i2c.transmit_buffer = self.classes[id].encode()
            lcd.display(img)
        except:
            pass

    def __deinit__(self):
        if self.kpu_net_obj:
            kpu.deinit(self.kpu_net_obj)
            del self.kpu_net_obj
            gc.collect()
            

