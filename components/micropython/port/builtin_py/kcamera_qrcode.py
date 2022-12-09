import sensor
import image
import lcd
import time
import ui
class KCameraQRCode:
    def __init__(self):
        self.name = 'qrcode'
        self.name2 = 'barcode'
        self.result = {
            'text': ''
        }

    def QrCode(self):
        img = sensor.snapshot()
        res = img.find_qrcodes()
        if len(res) > 0:
            img.draw_rectangle(0, 210, 320, 30, color=(255,128,0), thickness=1, fill=True)
            # self.result = str(res[0].payload()).encode('utf-8')
            text = str(res[0].payload())
            self.result['text'] = text
            # img.draw_string((320 - len(text) * 16) // 2, 220, text, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
            ui.DrawString(img, (320 - ui.GetStrLenFixed(text)) // 2, 220, text)
            # print(res[0].payload())
            
        else:
            self.result['text'] = ''
        # lcd.display(img)
        return img

    def BarCode(self):
        img = sensor.snapshot()
        res = img.find_barcodes()
        if len(res) > 0:
            img.draw_rectangle(0, 210, 320, 30, color=(255,128,0), thickness=1, fill=True)
            text = str(res[0].payload())
            self.result['text'] = text.encode()
            # img.draw_string((320 - len(text)* 16) // 2, 220, text, color=(255,255,255), scale=1, x_spacing=0, y_spacing=0, mono_space=True)
            ui.DrawString(img, (320 - ui.GetStrLenFixed(text)) // 2, 220, text)
            # print(res[0].payload())
            
        else:
            self.result['text'] = ''
        # lcd.display(img)
        return img

    def __deinit__(self):
        import gc
        gc.collect()