import sensor,lcd
import time
import kcamera_i2c
import kcamera_handler
from kcamera_objrec import KCamera_ObjectRec
import Maix
if (Maix.utils.gc_heap_size() != 1024*512):
    print('Change Heap Size...')
    Maix.utils.gc_heap_size(1024*512) # 600KB
print('Heap size if: %d' % Maix.utils.gc_heap_size())

# 初始化KCamera I2C设备(从机)
camera = kcamera_i2c.KCamera()
camera.KCamera_I2CInit()

while True:
    kcamera_i2c.handler.kc_action_proxy()
    