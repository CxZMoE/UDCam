'''
原理介绍
    算法的主要核心在于，讲整个画面分割出来5个ROI区域
    * 上方横向采样
    * 中间横向采样
    * 下方横向采样
    * 左侧垂直采样
    * 右侧垂直采样
    通过判断5个图片的组合关系给出路口类型的判断
'''
import sensor
import image
import time
import math
from GeometryFeature import GeometryFeature
import lcd
import ui
is_debug = True
DISTORTION_FACTOR = 1.15 # 畸变矫正因子
IMG_WIDTH  = 320        # 像素点宽度
IMG_HEIGHT = 240        # 像素点高度
def init_sensor():      # 初始化感光器
    # sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)  # 设置为灰度图
    sensor.set_framesize(sensor.QVGA)       # 设置像素大小
    sensor.skip_frames(time=2000)           # 最大像素点个数
    # sensor.set_auto_gain(False)           # 颜色追踪关闭自动增益
    # sensor.set_auto_whitebal(False)       # 颜色追踪关闭自动白平衡
    # sensor.set_hmirror(0)
    # sensor.set_vflip(1)
INTERSERCT_ANGLE_THRESHOLD = (45,90)        # 设置角度阈值

# 巡线的灰度阈值
LINE_COLOR_THRESHOLD = [(0, 50)]

# ROIS将镜头的画面分割为5个区域分别找寻色块
ROIS = {
    'down': (0, 200, 320, 40),
    'middle': (0, 100, 320, 40),
    'up': (0, 0, 320, 40),
    'left': (0, 0, 40, 240),
    'right': (280, 0, 40, 240)
}


class FindRouteBlobs():
    name = 'route'
    # ${路口类型}|${中直线坐标X}|${交叉路口中心坐标}
    result = {
        'type': None,
        'offset_x': 0,
        'cross_x': 0,
        'cross_y': 0
    }
    def __init__(self):
        init_sensor()

    def find_blobs_in_rois(self,img):
        '''
        在ROIS中寻找色块，获取ROI中色块的中心区域与是否有色块的信息
        '''
        global ROIS
        global is_debug
        roi_blobs_result = {}
        for roi_direct in ROIS.keys():
            roi_blobs_result[roi_direct] = {
                'cx': -1,
                'cy': -1,
                'blob_flag': False
            }
        for roi_direct, roi in ROIS.items():
            blobs=img.find_blobs(LINE_COLOR_THRESHOLD, roi=roi, merge=True, pixels_area=10)
            if len(blobs) == 0:
                continue
            largest_blob = max(blobs, key=lambda b: b.pixels())
            x,y,width,height = largest_blob[:4]
            if not(width >=5 and width <= 50 and height >= 5 and height <= 50):
                continue
            roi_blobs_result[roi_direct]['cx'] = largest_blob.cx()
            roi_blobs_result[roi_direct]['cy'] = largest_blob.cy()
            roi_blobs_result[roi_direct]['blob_flag'] = True
            if is_debug:
                img.draw_rectangle((x,y,width, height), color=(255))
        return roi_blobs_result

    def visualize_result(self, canvas, cx_mean, cx, cy, is_turn_left, is_turn_right, is_t, is_cross):
        '''
        可视化结果
        '''
        mid_x = int(canvas.width()/2)
        mid_y = int(canvas.height()/2)
        if not(is_turn_left or is_turn_right or is_t or is_cross):
            
            canvas.draw_circle(int(cx_mean), mid_y, 5, color=(255))
            canvas.draw_circle(mid_x, mid_y, 8, color=(0))
            canvas.draw_line((mid_x, mid_y, int(cx_mean), mid_y), color=(255))
        turn_type = 'N'   #判断为直线
        if is_t or is_cross:
            canvas.draw_cross(int(cx), int(cy), size=10, color=(255))
            canvas.draw_circle(int(cx), int(cy), 5, color=(255))
        if is_t:
            turn_type = 'T'  #判断为T字路口
        elif is_cross:
            turn_type = 'C'  #判断为十字路口
        elif is_turn_left:
            turn_type = 'L'  #判断为左转
        elif is_turn_right:
            turn_type = 'R'  #判断为右转
        else:
            # self.result = ('Unknown|0|0|0').encode('utf-8')
            self.result['type'] = None
        # ${路口类型}|${中直线坐标X}|${交叉路口中心坐标}
        # self.result = ('%s|%d|%d|%d' % (turn_type, cx_mean, cx, cy)).encode('utf-8')
        self.result['type'] = turn_type
        self.result['offset_x'] = cx_mean - mid_x
        self.result['cross_x'] = cx
        self.result['cross_y'] = cy
        # print(self.result)
        # canvas.draw_string(0, 0, turn_type, color=(0))
        ui.DrawString(canvas, 10, 30, "路口类型: " + turn_type)
    last_cx = 0
    last_cy = 0

    def Process(self):
        #拍取一张图片
        img = sensor.snapshot()
        img.lens_corr(DISTORTION_FACTOR)  #进行镜头畸形矫正，里面的参数是进行鱼眼矫正的程度

        lines = img.find_lines(threshold=1000, theta_margin = 50, rho_margin = 50)
        # intersect_pt = GeometryFeature.find_interserct_lines(lines, angle_threshold=(45,90), window_size=(IMG_WIDTH, IMG_HEIGHT))
        # if intersect_pt is None:
        #     intersect_x = 0
        #     intersect_y = 0
        # else:
        #     intersect_x, intersect_y = intersect_pt

        # 在5个区域(ROIS)中获取色块的状态
        result = self.find_blobs_in_rois(img)    # 返回5个色块的JSON
        is_turn_left = False
        is_turn_right = False

        # 检测转弯方向
        if (not result['up']['blob_flag'] ) and result['down']['blob_flag']:
            # 当上面没有色块，而下面有时，检测左右色块
            if result['left']['blob_flag']:
                is_turn_left = True             # 左转
            if result['right']['blob_flag']:
                is_turn_right = True            # 右转
        
        # 根据色块数量来确认路口类型
        is_t = False
        is_cross = False
        cnt = 0
        for roi_direct in ['up', 'down', 'left', 'right']:
            if result[roi_direct]['blob_flag']:
                cnt += 1
        is_t = cnt == 3         # T型路口
        is_cross = cnt == 4     # 十字路口

        # [直线时] 计算中直线的中心坐标(平均)
        cx_mean = 0
        for roi_direct in ['up', 'down', 'middle']:
            if result[roi_direct]['blob_flag']:
                cx_mean += result[roi_direct]['cx']
            else:
                cx_mean += IMG_WIDTH / 2
        cx_mean /= 3  #表示为直线时区域的中心x坐标

        # [交叉路口时] 计算交叉点中心坐标
        cx = 0        #cx,cy表示当测到为T型或者十字型的时候计算的交叉点的坐标
        cy = 0
        if is_cross or is_t:
            # 上下
            cnt = 0
            for roi_direct in ['up', 'down']:
                if result[roi_direct]['blob_flag']:
                    cnt += 1
                    cx += result[roi_direct]['cx']
            if cnt == 0:
                cx = last_cx
            else:
                cx /= cnt
            # 左右
            cnt = 0
            for roi_direct in ['left', 'right']:
                if result[roi_direct]['blob_flag']:
                    cnt += 1
                    cy += result[roi_direct]['cy']
            if cnt == 0:
                cy = last_cy
            else:
                cy /= cnt
        # 记录上一次的数据
        last_cx = cx
        last_cy = cy

        # Debug显示
        if is_debug:
            self.visualize_result(img, cx_mean, cx, cy, is_turn_left, is_turn_right, is_t, is_cross)
            # lcd.display(img)
        return img
    def __deinit__(self):
        import gc
        gc.collect()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
