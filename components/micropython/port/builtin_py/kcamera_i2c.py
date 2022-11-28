from micropython import const

from machine import I2C
import kcamera_handler
import gc
import time


I2C_TRANS_BUFFER_SIZE = const(1024)
# I2C Transmit Flags
I2C_TRANS_START = const(0x00)
I2C_TRANS_END   = const(0x02)

# 数据处理对象
handler = kcamera_handler.KCameraHandler()
class KCamera():
    k210_i2c = None
    def on_receive(self, data):
        pass

    def on_event(self, event):
        if event == I2C_TRANS_START:
            pass
        if event == I2C_TRANS_END:
            pass
    
    def __init__(self):
    # 初始化I2C设备并且返回对象
    # [on_recv]: 当设备接收到数据时候的回调
        pass
    def KCamera_I2CInit(self):
        # [I2C] 串口映射 & 初始化
        self.k210_i2c = I2C(I2C.I2C0, mode=I2C.MODE_SLAVE, scl=11, sda=12, freq=100000, addr=77,addr_size=7, 
            on_receive=self.on_receive, on_transmit=handler.on_transmit, on_event=self.on_event)
        
        return self.k210_i2c
    
    def process(self):
        handler.kc_action_proxy()



