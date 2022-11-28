import sensor, image, lcd
import KPU as kpu
from Maix import FPIOA, GPIO

import time
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

# 初始化保存人脸按钮
fpioa = FPIOA()
fpioa.set_function(16, FPIOA.GPIOHS8)
saveKey = GPIO(GPIO.GPIOHS8, GPIO.IN, GPIO.PULL_UP)
saveKey.irq(None ,GPIO.IRQ_FALLING)

