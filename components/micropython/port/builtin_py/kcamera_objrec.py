import sensor,lcd
import KPU as kpu
import gc
from micropython import const
import time, math
import ui
 # 操作
ACT_GET = b'get'

#模型分类，按照 20class 顺序
#“飞机”、“自行车”、“鸟”、“船”、“瓶子”、“公交车”、“汽车”、“猫”、“椅子”、“牛”、“餐桌”、
#“狗”、“马”、“摩托车”、“人”、“土豆植物”、“羊”、“沙发”、“火车”、“电视监视器”

#初始化 yolo2 网络，识别可信概率为 0.5（50%）
class KCamera_ObjectRec():
    classes = ['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable', 'dog', 'horse', 'motorbike', 'person', 'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor']
    classes_intl = ['飞机', '自行车', '鸟', '船', '瓶子', '公交车', '汽车', '猫', '椅子', '牛', '餐桌', '狗', '马', '摩托车', '人', '土豆植物', '羊', '沙发', '火车', '电视监视器']
    classes_count = [0] * 20
    anchor = (1.08, 1.19, 3.42, 4.41, 6.63, 11.38, 9.42, 5.11, 16.62, 10.52)
    name = 'obj'
    # KPU网络对象(kpu.init)
    kpu_net_obj = None

    # 识别结果
    result = {
        'id': None,
        'x': -1,
        'y': -1,
        'w': 0,
        'h': 0,
        'count': 0
    }
    def __init__(self):
        sensor.set_windowing((320, 240))
        # 首先加载物体的模型(KModel)
        self.kpu_net_obj = kpu.load(0x600000)
        kpu.init_yolo2(self.kpu_net_obj, 0.5, 0.3, 5, self.anchor)
        self.center = (320//2, 240//2)
    
    def VectorLen(self, vec_a, vec_b):
        vec = [0, 0, 0]
        for axis in range(len(vec_a)):
            vec[axis] = vec_a[axis] - vec_b[axis]

        # now vec is [x, y, z]
        # Calc Len
        return math.sqrt(vec[0]*vec[0] + vec[1]*vec[1] + vec[2]*vec[2])

    # 对图像进行处理，物体识别
    def process(self):
        for i in range(20):
            self.classes_count[i] = 0
        try:
            img = sensor.snapshot()
        except:
            return img
        items = kpu.run_yolo2(self.kpu_net_obj, img)
        # 遍历识别结果的对象
        if items:
            closest_index = -1
            closest_d = 320
            for i in range(len(items)):
                item = items[i]
                x,y,width,height = item.rect()
                # 去除宽度小于50px的
                # if width < 50 or height < 50:
                    # continue
                id = item.classid()
                # 为对象画框
                img.draw_rectangle(item.rect(), color=(255,128,0), thickness=1)
                img.draw_rectangle(x, y, ui.GetStrLenFixed(self.classes_intl[id]), 16, color=(255,128,0), thickness=1, fill=True)
                ui.DrawString(img, x, y, self.classes_intl[id])
                self.classes_count[id] += 1

                # 找最近的
                cx = x + width // 2
                cy = y + height // 2
                d = self.VectorLen(self.center, (cx, cy))
                if d < closest_d:
                    closest_d = d
                    closest_index = id

            # 为结果赋值(距离准星最近的)
            if closest_index < 0:
                # self.result = ('unknown|0').encode('utf-8')
                self.result['id'] = None
                self.result['x'] = cx
                self.result['y'] = cy
                self.result['w'] = width
                self.result['h'] = height

                self.result['count'] = 0
                return img
            count = 0
            for item in items:
                if item.classid() == closest_index:
                    count += 1
            # self.result = ('%s|%d' % (self.classes[closest_index], count)).encode('utf-8')
            self.result['count'] = count
            print_str = ('%s(%d个)' % (self.classes_intl[closest_index], count))
            img.draw_rectangle(0, 210, 320, 30, color=(255,128,0), thickness=1, fill=True)
            ui.DrawString(img, (320 - ui.GetStrLenFixed(print_str)) // 2, 220, print_str)
        else:
            self.result['id'] = None
            self.result['x'] = -1
            self.result['y'] = -1
            self.result['w'] = 0
            self.result['h'] = 0
            self.result['count'] = 0
        return img

    def __deinit__(self):
        if self.kpu_net_obj:
            kpu.deinit(self.kpu_net_obj)
            del self.kpu_net_obj
            gc.collect()
            

