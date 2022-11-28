import sensor
import image
import lcd
import KPU as kpu
import time
from Maix import FPIOA, GPIO
import gc
from fpioa_manager import fm

task_fd=None
task_ld=None
task_fe = None
task_load_re=0
a=None
clock = time.clock()

start_processing = False
BOUNCE_PROTECTION=50
last_key_state=1

key_pin=16 # 设置按键引脚 FPIO16
fpioa = FPIOA()
fpioa.set_function(key_pin,FPIOA.GPIOHS8)
key_gpio=GPIO(GPIO.GPIOHS8,GPIO.PULL_UP)



# 按键检测函数，用于在循环中检测按键是否按下，下降沿有效
def check_key():
    global last_key_state,start_processing,key_gpio
    val=key_gpio.value()
    print(key_gpio.value())
    if last_key_state == 1 and val == 0:
        time.sleep_ms(100)
        if key_gpio.value() == 0:
            start_processing=1
            print("star into face")
        else :start_processing=0
    else:
        start_processing=0
    last_key_state = val


anchor = (1.889, 2.5245, 2.9465, 3.94056, 3.99987, 5.3658, 5.155437,
          6.92275, 6.718375, 9.01025)  # anchor for face detect
dst_point = [(44, 59), (84, 59), (64, 82), (47, 105),(81, 105)]  # standard face key point position


def load_kmode():
    global task_fd,task_ld,task_fe,task_load_re,a,anchor
    task_fd = kpu.load(0x300000)
    task_ld = kpu.load(0x400000)
    task_fe = kpu.load(0x500000)
    a = kpu.init_yolo2(task_fd, 0.5, 0.3, 5, anchor)
    task_load_re=1


def del_kmode():
    global task_fd,task_ld,task_fe,task_load_re
    if task_load_re == 1:
        kpu.deinit(task_fd)
        kpu.deinit(task_ld)
        kpu.deinit(task_fe)
        task_load_re=0
        time.sleep_ms(50)
    else :
        pass

modes=0  #模式标志位
img_lcd = image.Image()
img_face = image.Image(size=(128, 128))
a = img_face.pix_to_ai()

record_ftr = []
record_ftrs = []
feature=0
names = []
namess=['ID1','ID2','ID3','ID4','ID5','ID6','ID7','ID8','ID9']
ACCURACY=80

class KCamera_FaceRec():
    def __init__(self):
        pass

    #功能：保存人脸信息和特征值
    #save_face
    #入口参数：无
    #返回值：无
    def save_face(self):
        global names,feature,record_ftrs,modes
        if modes ==1:
            ret=[]

            try:
                f = open("recordftr3.txt", "a+")
            except OSError:
                import os
                f = open("recordftr3.txt", "w")
                f.close()
                time.sleep_ms(100)
            
            with open("recordftr3.txt", "a+") as f:
                while(1):
                    line = f.readline()      #读取一行
                    if not line :
                        for a in range(0,len(names)):
                            if names[a] not in ret:   #存在
                                record_ftrs.append(feature)
                                f.write(names[a]+'#'+str(feature))  #信息写入文件
                                f.write("\n")
                                break
                        break
                    temp=line[0:line.index('#')]
                    ret.append(temp)              # 读取函数里面的人名
                    print(ret)
        else :
            record_ftrs.append(feature)

    #功能：读取人脸信息和特征值
    #名称：read_save_face
    #入口参数：无
    #返回值：无
    def read_save_face(self):
        global record_ftr,names,modes
        if modes == 1 :
            with open("recordftr3.txt", "a+") as f:
                f.seek(0)
                while(1):
                    line = f.readline()
                    if not line:
                        break
                    name = line[0:line.index('#')]   #获取姓名
                    names.append(name)   #追加到姓名列表
                    line = line[line.index('#')+1:]      #截取人脸特征
                    record_ftrs.append(eval(line))       #向人脸特征列表中添加已存特征
        else:
            pass

    #功能：删除某一个人脸
    #名称 ：del_save_face
    #入口参数：人脸的名字
    #返回值：无
    def del_save_face(self, name):
        global record_ftr,names
        transit=''
        ret=[]
        linenum1=0
        linenum2=1
        with open("recordftr3.txt",'w') as f:
            while(1):
                line = f.readline()      #读取一行
                if not line:
                    if len(ret)>0:
                        for a in range(0,len(ret)):
                            if name == ret[a]:
                                linenum1=a+1
                        if linenum1 ==0:
                            print("the face not enter")
                        break
                    else :
                        print("no face")
                        break
                temp=line[0:line.index('#')]
                ret.append(temp)
        with open("recordftr3.txt",'w') as f:
            for lines in f:
                if linenum2 ==linenum1:
                    linenum2+=1
                    continue
                else:
                    transit+=lines
                    linenum2+=1
        with open("recordftr3.txt",'w') as f:
            f.write(transit)
        record_ftrs.clear()
        names.clear()
        self.read_save_face()



    #功能：删除所有人脸
    #名称：del_all_save_face
    #入口参数：无
    #返回值：无
    def del_all_save_face(self):
        global record_ftr,names
        with open("recordftr3.txt",'w') as f:
            f.close()
        record_ftrs.clear()
        names.clear()


    #功能：改变人脸识别模式
    #函数名称 change_mode
    #入口参数：mode 字符串
    #返回值：无
    def change_mode(self, mode):
        global modes,names,record_ftrs
        if mode == '01':
            modes =1
            record_ftrs.clear()
            names.clear()
            self.read_save_face()
        elif mode == '02':
            modes =0
            record_ftrs.clear()
            names.clear()
        else:
            pass

    #人脸识别主程序
    #功能：实现人脸识别
    #入口参数：uart：串口对象，用来发送串口数据 ，name ：加入人脸识别姓名的列表
    #返回值：无
    def fr(self,name):
        global start_processing,a,task_fd,task_ld,task_fe,feature,names,modes
        for i in range(0,len(name)):   # 读取人名，保存模式人名
            if name[i] not in names:   #如果没有重复
                names.append(name[i])       #添加人脸
                print(names)
        img = sensor.snapshot()
        clock.tick()
        check_key()
        code = kpu.run_yolo2(task_fd, img)
        if code:
            for i in code:
                # Cut face and resize to 128x128
                a = img.draw_rectangle(i.rect())
                face_cut = img.cut(i.x(), i.y(), i.w(), i.h())
                face_cut_128 = face_cut.resize(128, 128)
                a = face_cut_128.pix_to_ai()
                # a = img.draw_image(face_cut_128, (0,0))
                # Landmark for face 5 points
                fmap = kpu.forward(task_ld, face_cut_128)
                plist = fmap[:]
                le = (i.x() + int(plist[0] * i.w() - 10), i.y() + int(plist[1] * i.h()))
                re = (i.x() + int(plist[2] * i.w()), i.y() + int(plist[3] * i.h()))
                nose = (i.x() + int(plist[4] * i.w()), i.y() + int(plist[5] * i.h()))
                lm = (i.x() + int(plist[6] * i.w()), i.y() + int(plist[7] * i.h()))
                rm = (i.x() + int(plist[8] * i.w()), i.y() + int(plist[9] * i.h()))
                # align face to standard position
                src_point = [le, re, nose, lm, rm]
                T = image.get_affine_transform(src_point, dst_point)
                a = image.warp_affine_ai(img, img_face, T)
                a = img_face.ai_to_pix()
                # a = img.draw_image(img_face, (128,0))
                del (face_cut_128)
                # calculate face feature vector
                fmap = kpu.forward(task_fe, img_face)
                feature = kpu.face_encode(fmap[:])
                reg_flag = False
                scores = []
                for j in range(len(record_ftrs)):
                    score = kpu.face_compare(record_ftrs[j], feature) #迭代每一个特征值
                    scores.append(score)                    #加入score
                max_score = 0
                index = 0
                for k in range(len(scores)):                # 迭代最高分数
                    if max_score < scores[k]:
                        max_score = scores[k]
                        index = k                           #第几个分数最相似
                if max_score > ACCURACY:
                    if modes ==1:
                        a = img.draw_string(i.x(), i.y(), ("%s" % (
                            names[index])), color=(0, 255, 0), scale=2)
                        self.result = 'face|03|'+names[index]     #得出人脸
                    else:
                        a = img.draw_string(i.x(), i.y(), ("%s" % (
                            namess[index])), color=(0, 255, 0), scale=2)
                        self.result = 'face|03|'+namess[index]     #得出人脸
                else:
                    a = img.draw_string(i.x(), i.y(), ("x"), color=(255, 0, 0), scale=2)
                    self.result = "face|02"
                if start_processing:
                    self.save_face()
                    start_processing = False
                break
        else:
            self.result = "face|01"
        fps = clock.fps()
        print("%2.1f fps" % fps)
        a = lcd.display(img)



