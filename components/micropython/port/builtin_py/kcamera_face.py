import sensor
import image
import lcd
import KPU as kpu
import time
from Maix import FPIOA, GPIO
from fpioa_manager import fm
import gc
import ui
# 设置按键
fm.register(35, fm.fpioa.GPIOHS8)
key_gpio=GPIO(GPIO.GPIOHS8,GPIO.PULL_UP)

# 人脸检测的锚点
anchor = (1.889, 2.5245, 2.9465, 3.94056, 3.99987, 5.3658, 5.155437,
          6.92275, 6.718375, 9.01025)
# 关键点检测的位置(标准的)
dst_point = [(44, 59), (84, 59), (64, 82), (47, 105),
             (81, 105)]

cfg = 'kcamera_face.cfg'

class KCamera_Face():
    name = 'face'
    result = {
        'id': None,
        'x': -1,
        'y': -1,
        'w': 0,
        'h': 0,
        'score': 0
    }
    def __init__(self):
        ## 使用到的模型
        # 1.人脸检测模型
        self.task_fd = kpu.load('/sd/models/FaceDetection.smodel')
        # 2.人脸关键点检测模型
        self.task_ld = kpu.load('/sd/models/FaceLandmarkDetection.smodel')
        # 3.人脸特征提取模型
        self.task_fe = kpu.load('/sd/models/FeatureExtraction.smodel')
        print('run taskfd')
        kpu.init_yolo2(self.task_fd, 0.5, 0.3, 5, anchor)
        print('run taskfd end')
        # 需要一张照片
        self.img_lcd = image.Image()
        # 然后裁剪成 (128, 128) 大小
        self.img_face = image.Image(size=(128, 128))
        self.img_face.pix_to_ai()
        # 准确度
        self.ACCURACY = 85
        # 反弹保护
        self.BOUNCE_PROTECTION = 100

        self.record_ftr = []
        self.record_ftrs = []
        # self.names = ['Mr.1', 'Mr.2', 'Mr.3', 'Mr.4', 'Mr.5',
        #     'Mr.6', 'Mr.7', 'Mr.8', 'Mr.9', 'Mr.10']
        self.custom_names = []
        self.start_processing = False
        self.FSLoadFace()
    
    def set_key_state(self):
        if (key_gpio.value() == 0):
            time.sleep_ms(self.BOUNCE_PROTECTION)
            if (key_gpio.value() == 1):
                print('do processing')
                self.start_processing = True

    def GetFaceImg(self):
        img = sensor.snapshot()
        # 执行人脸检测
        code = kpu.run_yolo2(self.task_fd, img)
        if code:
            for face in code:
                face_img_128 = img.cut(face.x(), face.y(), face.w(), face.h()).resize(128, 128)
                face_img_128.pix_to_ai()
                ## 获取人脸特征图结果
                fmap = kpu.forward(self.task_ld, face_img_128)
                plist = fmap[:]
                # 左眼
                le = (face.x() + int(plist[0] * face.w() - 10), face.y() + int(plist[1] * face.h()))
                # 右眼
                re = (face.x() + int(plist[2] * face.w()), face.y() + int(plist[3] * face.h()))
                # 鼻子
                nose = (face.x() + int(plist[4] * face.w()), face.y() + int(plist[5] * face.h()))
                # 左嘴角
                lm = (face.x() + int(plist[6] * face.w()), face.y() + int(plist[7] * face.h()))
                # 右嘴角
                rm = (face.x() + int(plist[8] * face.w()), face.y() + int(plist[9] * face.h()))

                ## 进行标记
                img.draw_circle(le[0], le[1], 4)
                img.draw_circle(re[0], re[1], 4)
                img.draw_circle(nose[0], nose[1], 4)
                img.draw_circle(lm[0], lm[1], 4)
                img.draw_circle(rm[0], rm[1], 4)

                # 通过标记点进行仿射变换
                src_point = [le, re, nose, lm, rm]
                T = image.get_affine_transform(src_point, dst_point)
                image.warp_affine_ai(img, self.img_face, T)
                
                del face_img_128

                # 计算人脸特征值向量
                fmap = kpu.forward(self.task_fe, self.img_face)
                feature = kpu.face_encode(fmap[:])
                scores = []
                for j in range(len(self.record_ftrs)):
                    score = kpu.face_compare(self.record_ftrs[j], feature)
                    scores.append(score)
                max_score = 0
                index = 0
                for k in range(len(scores)):
                    if max_score < scores[k]:
                        max_score = scores[k]
                        index = k
                
                if max_score > self.ACCURACY:
                    ui.DrawString(img, face.x(), face.y(), ("%s: %2.1f" % (self.custom_names[index], max_score)), color=(0, 255, 0))
                    # img.draw_string(face.x(), face.y(),
                    #     ("%s :%2.1f" % (self.custom_names[index], max_score)),
                    #     color=(0, 255, 0), scale=1, x_spacing=0, y_spacing=0
                    # )
                    # self.result = ('%s|%d|%d|%d' % (self.custom_names[index], face.x() + face.w() // 2, face.y() + face.h()//2, int(max_score))).encode('utf-8')
                    self.result['id'] = self.custom_names[index]
                    self.result['x'] = face.x() + face.w() // 2
                    self.result['y'] = face.y() + face.h() // 2
                    self.result['w'] = face.w()
                    self.result['h'] = face.h()
                    self.result['score'] = max_score
                else:
                    # img.draw_string(face.x(), face.y(),
                    #     ("X :%2.1f" % (max_score)),
                    #     color=(255, 0, 0), scale=1, x_spacing=0, y_spacing=0
                    # )
                    ui.DrawString(img, face.x(), face.y(), ("X: %2.1f" % (max_score)), color=(0, 255, 0))
                    self.result['id'] = None
                    self.result['x'] = face.x() + face.w() // 2
                    self.result['y'] = face.y() + face.h() // 2
                    self.result['w'] = face.w()
                    self.result['h'] = face.h()
                    self.result['score'] = max_score

                # 处理保存人脸按键
                if self.start_processing:
                    self.record_ftr = feature
                    self.record_ftrs.append(feature)
                    self.start_processing = False
        # lcd.display(img)
        return img

    # 添加人脸
    def AddFace(self, name):
        try:
            _ = self.custom_names.index(name)
        except:
            self.custom_names.append(name)
            return
        print('[ERR] 要添加的人脸已在列表中')

    # 删除人脸
    def DelFace(self, name):
        try:
            self.custom_names.remove(name)
        except:
            print('[ERR] 要删除的人脸不在列表中')
    
    # 删除所有人脸
    def DelAllFace(self):
        self.custom_names = []
        import os
        try:
            os.remove(cfg)
        except:
            pass


    # 保存人脸到本地
    def FSSaveFace(self):
        ftrs = []
        names = []
        if len(self.custom_names) < len(self.record_ftrs):
            ftrs = self.record_ftrs[:len(self.custom_names)]
            names = self.custom_names[:]
        elif len(self.custom_names) > len(self.record_ftrs):
            ftrs = self.record_ftrs[:]
            names = self.custom_names[:len(self.record_ftrs)]
        else:
            ftrs = self.record_ftrs[:]
            names = self.custom_names[:]

        with open(cfg, 'wb') as f:
            data = {}
            for i in range(len(ftrs)):
                ftr = []
                for num in ftrs[i]:
                    ftr.append(num)
                data.update({names[i]: ftr})
            # print(data)
            import json
            f.write(json.dumps(data))

    # 从本地加载人脸
    def FSLoadFace(self):
        import json
        try:
            with open(cfg, 'rb') as f: 
                data = json.loads(f.read())
                # print(data)
                for face in data:
                    self.custom_names.append(face)
                    self.record_ftrs.append(bytearray(data[face]))
                
                print('Loaded Ftrs:', self.record_ftrs)
                print('Loaded Names:', self.custom_names)
        except Exception as e:
            print(e)

    
    def Fr(self):
        self.set_key_state()
        return self.GetFaceImg()

    def __deinit__(self):
        kpu.deinit(self.task_fd)
        del self.task_fd
        kpu.deinit(self.task_ld)
        del self.task_ld
        kpu.deinit(self.task_fe)
        del self.task_fe
        gc.collect()
        