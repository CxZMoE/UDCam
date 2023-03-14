import KPU as kpu
import sensor
import lcd
from Maix import GPIO
from fpioa_manager import fm
from board import board_info
import time
import gc
import os
from kcamera_color import *
import ui
# 操作
KC_ACT_LOADMODE = 'load'
ACT_GET = 'get'
ACT_UPDATE_SAVE_NAME = 'update'


class KCameraSelfLearning():
    result = {
        'id': 'Unknown',
        'color': 'Unknown',
        'min_dist': 0
    }
    result_index = 0
    name = 'self_learning'
    classifier_name = ''
    default_load_mode = 0
    load_mode = 0
    def __init__(self, num, key_save):
        sensor.set_windowing((224, 224))
        fm.register(35, fm.fpioa.GPIOHS8)
        
        self.update(num)
        self.THRESHOLD = 8
        self.class_names = ['1', '2', '3', '4']
        self.colors_reconize = ColorUtils()
        self.key = GPIO(GPIO.GPIOHS8,GPIO.PULL_UP)
        self.key_save = key_save
        # 加载模型文件
        # self.model = kpu.load('/sd/models/self_learn_classifier_lite.smodel')
        self.model = kpu.load(0x300000)
        
        self.update_save_name('default.classifier')
        self.cap_num = 0
        self.train_status = 0
        self.last_cap_time = 0
        self.last_btn_status = 1
        self.classifier = None

    # 开始处理自学习
    def star_learn(self):
        try:
            img = sensor.snapshot()
        except:
            return
        
        img.pix_to_ai()
        # img = img_return.copy(roi=(48, 8, 224, 224))
        img_return = img.cut(0, 28, 224, 168)
        img_return = img_return.resize(320, 240)
        # img = img.rotation_corr(z_rotation=90)
        
        color = self.colors_reconize.GetColor(img_return)
        if self.load_mode != 1:
            if self.key_save.value() == 0 and self.train_status == 0:  # 如果按键按下
                self.default_load_mode = 1
                self.load_save_learn()
                time.sleep_ms(50)  # 消抖
        
        if self.default_load_mode == 1 or self.load_mode == 1:
            self.load_self_learning_mode(img_return, img, color)
            return img_return
        if self.train_status == 0:
            if self.key.value() == 0:
                time.sleep_ms(30)
                if self.key.value() == 0 and (self.last_btn_status == 1) and (time.ticks_ms() - self.last_cap_time > 500):
                    print(img)
                    print(img_return)
                    self.last_btn_status = 0
                    self.last_cap_time = time.ticks_ms()
                    if self.cap_num < self.class_num:
                        index = self.classifier.add_class_img(img)
                        self.cap_num += 1
                        print("add class img:", index)
                    elif self.cap_num < self.class_num + self.sample_num:
                        index = self.classifier.add_sample_img(img)
                        self.cap_num += 1
                        print("add sample img:", index)
                        # for b in range(0,6):
                        #     if b <1:
                        #         index = self.classifier.add_class_img(img)  #加入一个根目标
                        #         self.cap_num += 1                           #跟目标加1
                        #     else:
                        #         index = self.classifier.add_sample_img(img)
                else:
                    ui.DrawString(img_return, 10, 187, "请松开BOOT键", color=(0,255,0))
            else:
                time.sleep_ms(30)
                if self.key.value() == 1 and (self.last_btn_status == 0):
                    self.last_btn_status = 1
                if self.cap_num < self.class_num:
                    ui.DrawString(img_return, 10, 187, "按下按键捕捉分类:" + self.class_names[self.cap_num], color=(0,255,0))
                elif self.cap_num < self.class_num + self.sample_num:
                    ui.DrawString(img_return, 10, 187, "按下按键捕捉样本{}".format(self.cap_num-self.class_num), color=(0,255,0))
            self.result['id'] = None
        # train and predict
        if self.train_status == 0:
            if self.cap_num >= self.class_num + self.sample_num:
                print("start train")
                ui.DrawString(img_return, 10, 187, "训练中...", color=(0,255,0))
                # lcd.display(img)
                self.classifier.train()
                print("train end")
                self.train_status = 1
        else:
            res_index, min_dist = self.classifier.predict(img)
            if res_index >= 0 and min_dist < self.THRESHOLD:
                # self.result = ('modeobj|{}|{}'.format(
                    # self.class_names[res_index], color)).encode()
                self.result['id'] = self.class_names[res_index]
                self.result['color'] = color
                self.result['min_dist'] = min_dist
                # print(self.result)
                str_print = self.result['id']
                len_str = ui.GetStrLenFixed(str_print)
                img_return.draw_rectangle(320 - len_str - 20, 180, len_str + 20, 30, color=(255,128,0), thickness=1, fill=True)
                ui.DrawString(img_return, 320 - len_str - 5, 187, str_print, color=(0,255,0))
            else:
                # self.result = ('modeobj|Unknown|{}'.format(color)).encode()
                self.result['id'] = 'Unknown'
                self.result['color'] = color
                self.result['min_dist'] = min_dist
                # print(self.result)

            self.save_the_local_system(
                self.save_name, img_return)                        # 根据按键保存自学习本地模型
            # print(a)
        # lcd.display(img)
        gc.collect()
        return img_return

    def load_classifier(self):
        self.classifier = kpu.classifier(
            self.model, self.class_num, self.sample_num, fea_len=512)
        print("class num: {} sample num: {}\n".format(
            self.class_num, self.sample_num))

    def load_self_learning_mode(self, img_return=None, img=None, color=None):  # 加载自学习\
        if img == None:
            try:
                img = sensor.snapshot()
            except:
                print('pass')
                self.result = b''
                return
        if color == None:
            color = self.colors_reconize.GetColor(img)
        try:
            res_index, min_dist = self.classifier.predict(img)
        except Exception as e:
            print('predict err:', e)
            # self.result = ('modeobj|Unknown|{}'.format(color)).encode()
            self.result['id'] = 'Unknown'
            self.result['color'] = color
            self.result['min_dist'] = min_dist
            # lcd.display(img)
            return

        if res_index >= 0 and min_dist < self.THRESHOLD:
            ui.DrawString(img_return, 10, 187, self.class_names[res_index], color=(0,255,0))
            self.result['id'] = self.class_names[res_index]
            self.result['color'] = color
            self.result['min_dist'] = min_dist
        else:
            self.result['id'] = 'Unknown'
            self.result['color'] = color
            self.result['min_dist'] = min_dist
        # print("{:.2f}".format(min_dist))
        # print(self.result)
        # lcd.display(img)
        return img
        # gc.collect()

    def update(self, Num):  # 更新数量,后期使用
        self.class_num = Num
        self.sample_num = Num*5

    def update_save_name(self, name):        # 更新保存名字
        self.save_name = name

    def save_self_learning(self):  # 保存自学习到文件系统
        self.classifier.save(self.save_name)

    def save_the_local_system(self, name, img):
        # 保持之前先尝试删除文件
        if self.key_save.value() == 0:  # 如果按键按下
            time.sleep_ms(50)  # 消抖
            print('key pressed')
            print('name:' + str(name))
            if name:
                flash_ls = os.listdir()
                print('dir:' + str(flash_ls))
                if name not in flash_ls:
                    self.train_status = 3
                    print(self.classifier.save(name))  # 保存至文件系统
                    ui.DrawString(img, 10, 187, "保存成功", color=(0,255,0))
                    del flash_ls
                    return 1
                else:
                    del flash_ls
                    print("the name is already")
                    ui.DrawString(img, 10, 187, "已经保存过...", color=(0,255,0))
                    return 0
            else:
                pass
                print("no name")

    def load_save_learn(self, load_name='default.classifier'):
        print("加载保存的文件:", load_name)
        if (self.classifier_name != load_name):
            self.classifier, self.class_num, self.sample_num = kpu.classifier.load(
                self.model, load_name, fea_len=512)
            prefix = load_name.split('.')[0]
            for i in range(len(self.class_names)):
                self.class_names[i] = "{}_{}".format(prefix, i+1)
            self.classifier_name = load_name
            gc.collect()
            return 1
        else:
            return 1

    def __deinit__(self):
        sensor.set_windowing((320, 240))
        if self.model:
            kpu.deinit(self.model)
            del self.model
            gc.collect()
