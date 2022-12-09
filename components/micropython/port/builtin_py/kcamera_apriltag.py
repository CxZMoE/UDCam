import sensor
import image
import math
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240


class KCameraAprilTag():
    name = 'april_tag'
    result = {}
    def __init__(self):
        self.roi = (SCREEN_WIDTH//2-75, SCREEN_HEIGHT//2-75, 150, 150)
        self.fx = (1.8 / 3.6736 ) * 2624
        self.fy = (1.8 / 2.7384) * 1964
        self.cx = SCREEN_WIDTH // 2
        self.cy = SCREEN_HEIGHT // 2
        self.k = -1
        self.test_degree = 0
        pass
    
    def Process(self):
        # 拍一张照片
        img = sensor.snapshot()
        # 找AprilTag
        tags = img.find_apriltags(roi=self.roi, fx=self.fx, fy=self.fy, cx=self.cx, cy=self.cy)
        img.draw_rectangle(self.roi, color=(255,255,0))
        if self.test_degree == 90:
            self.test_degree = 0
        else:
            self.test_degree = 90
        # self.test_degree += 1
        if tags:
            for tag in tags:
                rect = tag.rect()
                # 给标签画框框
                img.draw_rectangle(rect, color=(255,168,0))
                
                # 画箭头
                rotation = tag.rotation()

                # 原点移动
                cx = tag.x() + tag.w()//2
                cy = tag.y() + tag.h()//2
                
                # 计算坐标
                len_b = 50
                x = int((-len_b * math.sin(rotation)) + cx)
                y = int((-len_b * math.cos(rotation)) + cy)
                # print ('angle: %d x: %d y: %d, ox: %d, oy: %d' % (rotation, x, y, len_b * math.sin(rotation), len_b * math.cos(rotation)))
                img.draw_arrow(cx,cy,x,y, color=(255,0,0))

                data = {
                    'tag_id': tag.id(),
                    'tag_family': tag.family(),
                    'cx': cx,
                    'cy': cy,
                    'rect': tag.rect(),
                    'rotation': rotation,
                    'translation_3d': (tag.x_translation(), tag.y_translation(), tag.z_translation()),
                    'ratation_3d': (self.ToDegree(tag.x_rotation()), self.ToDegree(tag.y_rotation()), self.ToDegree(tag.z_rotation()))
                }
                self.result = data
                print(data)
        return img
    def ToDegree(self, rad):
        return rad * (180 / math.pi)
    def Calibrate(self, x, y, z, measure_d=10, timeout=3000):
        import time
        st = time.ticks_ms()
        while time.ticks_ms() - st < timeout:
            img = sensor.snapshot()
            tags = img.find_apriltags(roi=self.roi, fx=self.fx, fy=self.fy, cx=self.cx, cy=self.cy)
            if tags:
                tag = tags[0]
                x = tag.x_translation()
                y = tag.y_translation()
                z = tag.z_translation()
                import math
                # 计算距离系数k=实测距离/获取距离
                self.k = measure_d / math.sqrt(x*x + y*y + z*z)
                return self.k
        return -1

    def GetDistance(self, x, y, z):
        import math
        d = math.sqrt(x*x + y*y + z*z)
        return self.k * d

    def Test(self):
        import lcd
        while True:
            img = self.Process()
            lcd.display(img)

    def __deinit__(self):
        import gc
        gc.collect()