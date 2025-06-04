import rtde
import time

try:
    rtde.init()
    time.sleep(1)
    for i in range(5):
        rtde.setInt3([1, 2, 3])
        time.sleep(5)
        rtde.setInt3([1, 22, 3])
        time.sleep(5)
except Exception as e:
    print(e)
    pass
finally:
    rtde.pause()
    rtde.stop()
