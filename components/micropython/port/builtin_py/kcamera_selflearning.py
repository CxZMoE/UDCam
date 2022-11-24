import KPU as kpu
import sensor,lcd
from Maix import GPIO
from fpioa_manager import fm
from board import board_info
import time
import gc,os
from reconize_blobs import *

 # 操作
KC_ACT_LOADMODE = b'load'
ACT_GET = b'get'
ACT_UPDATE_SAVE_NAME = b'update'

class KCameraSelfLearning():
    result = b''
    result_index = 0
    process = None
    def __init__(self, num, key_save):
        sensor.set_windowing((224, 224))
        fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0)
        self.update(num)
        self.THRESHOLD = 8
        self.class_names = ['1', '2', '3', '4']
        self.colors_reconize=reconize_blobs_for_search()
        self.key = GPIO(GPIO.GPIOHS0, GPIO.PULL_UP)
        self.key_save = key_save
        # try:
        #     self.model = kpu.load_flash(0x300000, 1, 0x4000, 80000000)
        # except:
        #     print('该模型不支持load_flash')
        self.model = kpu.load(0x300000)

        self.update_save_name(0)
        self.cap_num = 0
        self.train_status = 0
        self.last_cap_time = 0
        self.last_btn_status = 1
        self.classifier = None

    # 在图像上写入文字
    def draw_string(self,img, x, y, text, color, scale, bg=None):
        if bg:
            img.draw_rectangle(x-2,y-2, len(text)*8*scale+4 , 16*scale, fill=True, color=bg)
        img = img.draw_string(x, y, text, color=color,scale=scale)
        return img

    # 开始处理自学习
    def star_learn(self):
        try:
            img = sensor.snapshot()
        except:
            return
        self.colors_reconize.update_roi(roi=(100,100,40,40))
        self.colors_reconize.update_img(img)
        color=self.colors_reconize.get_colors_on_screen()

        # img = img.rotation_corr(z_rotation=90)
        # img.pix_to_ai()

        if self.train_status == 0:
            if self.key.value() == 0:
                time.sleep_ms(30)
                if self.key.value() == 0 and (self.last_btn_status == 1) and (time.ticks_ms() - self.last_cap_time > 500):
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
                    img =self.draw_string(img, 2, 200, "release key please", color=lcd.GREEN,scale=1)
            else:
                time.sleep_ms(30)
                if self.key.value() == 1 and (self.last_btn_status == 0):
                    self.last_btn_status = 1
                if self.cap_num < self.class_num:
                    img = self.draw_string(img, 0, 200, "press key to cap "+self.class_names[self.cap_num], color=lcd.WHITE,scale=1, bg=lcd.GREENYELLOW)
                elif self.cap_num < self.class_num + self.sample_num:
                    img = self.draw_string(img, 0, 200, " key to cap sample{}".format(self.cap_num-self.class_num), color=lcd.WHITE,scale=1, bg=lcd.RED)
            self.result = ('modeobj|Unknown|{}'.format(color)).encode()
            self.result_index = 0
        # train and predict
        if self.train_status == 0:
            if self.cap_num >= self.class_num + self.sample_num:
                print("start train")
                img = self.draw_string(img, 30, 100, "training...", color=lcd.WHITE,scale=2, bg=lcd.RED)
                lcd.display(img)
                self.classifier.train()
                print("train end")
                self.train_status = 1
        else:
            res_index, min_dist = self.classifier.predict(img)
            if res_index >= 0 and min_dist < self.THRESHOLD :
                self.result = ('modeobj|{}|{}'.format(self.class_names[res_index],color)).encode()
                self.result_index = 0
                print(self.result)
                img = self.draw_string(img, 2, 2, self.class_names[res_index], color=lcd.WHITE,scale=2, bg=lcd.GREENYELLOW)
            else:
                self.result = ('modeobj|Unknown|{}'.format(color)).encode()
                self.result_index = 0
                print(self.result)
            
            a=self.save_the_local_system(self.save_name,img)                        # 根据按键保存自学习本地模型
            # print(a)
        lcd.display(img)

    def load_classifier(self): #加载文件系统中的自学习文件
        self.classifier = kpu.classifier(self.model, self.class_num, self.sample_num, fea_len=512)
        print("class num: {} sample num: {}\n".format(self.class_num, self.sample_num))

    def load_self_learning_mode(self): # 加载自学习\
        try:
            img = sensor.snapshot()
        except:
            print('pass')
            self.result = b''
            return
        self.colors_reconize.update_roi(roi=(100,100,40,40))
        self.colors_reconize.update_img(img)
        color=self.colors_reconize.get_colors_on_screen()
        try:
            res_index, min_dist = self.classifier.predict(img)
        except Exception as e:
            print('predict err:', e)
            self.result = ('modeobj|Unknown|{}'.format(color)).encode()
            self.result_index = 0
            lcd.display(img)
            return

        if res_index >= 0 and min_dist < self.THRESHOLD :
            img = self.draw_string(img, 2, 2, self.class_names[res_index], color=lcd.WHITE,scale=2, bg=lcd.RED)
            self.result = ('modeobj|{}|{}'.format(self.class_names[res_index],color)).encode()
            self.result_index = 0
        else:
            self.result = ('modeobj|Unknown|{}'.format(color)).encode()
            self.result_index = 0
        print("{:.2f}".format(min_dist))
        print(self.result)
        lcd.display(img)

    def update(self,Num):      #更新数量,后期使用
        self.class_num = Num
        self.sample_num = Num*5 

    def update_save_name(self,name):        # 更新保存名字
        self.save_name = name

    def save_self_learning(self):           #保存自学习到文件系统
        self.classifier.save(self.save_name)

    def save_the_local_system(self,name,img):
        if self.key_save.value() == 0:            #如果按键按下
            time.sleep_ms(50)                       #消抖
            print('key pressed')
            print('name:' + str(name))
            if name:
                flash_ls= os.listdir()  
                print('dir:' + str(flash_ls))                     
                if name not in flash_ls:
                    self.classifier.save(name)        #保存至文件系统
                    self.draw_string(img, 2, 2, "succeed save", color=lcd.WHITE,scale=2, bg=lcd.GREENYELLOW)
                    del flash_ls
                    return 1
                else :
                    del flash_ls
                    print("the name is already")
                    self.draw_string(img, 2, 2, "the name is already save", color=lcd.WHITE,scale=2, bg=lcd.GREENYELLOW)
                    return 0
            else :
                pass
                print("no name")


    def load_save_learn(self,load_name):
        print("加载保存的文件:", load_name)
        try:
            self.classifier,self.class_num,self.sample_num = kpu.classifier.load(self.model,load_name, fea_len=512)
            prefix = load_name.split('.')[0]
            for i in range(len(self.class_names)):     
                self.class_names[i] = "{}_{}".format(prefix, i+1)
            return 1
        except:
            return 0

    def __deinit__(self):
        self.process = None
        if self.model:
            kpu.deinit(self.model)
            del self.model
            gc.collect()
        



