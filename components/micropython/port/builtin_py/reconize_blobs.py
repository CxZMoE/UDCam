import sensor,image,lcd,time
import KPU as kpu
import gc, sys
 

# ai_color|circle|color
class reconize_blobs_for_search():
    def __init__(self):
        self.update_roi()
        
    def update_roi(self,roi=(0,0,0,0)):
        self.roi=roi
        
    def update_img(self,img):
        self.img=img
        self.img.draw_rectangle(self.roi,color=(228,247,70))
       # lcd.display(self.img)

    def back_color_on_re(self,color_l,color_a,color_b):
        temp_lab_color=(color_l,color_a,color_b)
        temp_rgb_color=image.lab_to_rgb(temp_lab_color)
        return temp_rgb_color

    def reconize_fb(self):
        sta=self.img.get_statistics(roi=self.roi)
        color_Ll=sta.l_mode()           #获取lab值
        color_Al=sta.a_mode()
        color_Bl=sta.b_mode()
        rgb=self.back_color_on_re(color_Ll,color_Al,color_Bl)
        return rgb

    def get_colors_on_screen(self):
        rgb=self.reconize_fb()
        temp_r=rgb[0]  #判断第一个r
        temp_g=rgb[1]
        temp_b=rgb[2]
        if temp_r <120:    #往黑走
            if temp_g <120: #黑走
                if temp_b <120: #黑走
                    color_s ='black'
                else :      # 蓝
                    color_s ='blue'
            else:               # 往绿走
                if temp_b < 120 :                
                    color_s ='green'
                else : color_s='Cyan'
        else:               #往白走
            if temp_g < 120 :  #  
                if temp_b <120 :
                    color_s ='red'
                else:
                    color_s ='pirple'
            else :
                if temp_b < 120:
                    color_s ='yellow'
                else :
                    color_s = 'white'
        # print(color_s)
        return color_s

class ai_color_shape():
    def __init__(self):
        sensor.set_windowing((224, 224))
        self.color_s=reconize_blobs_for_search()
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


                


        


            


        
        

