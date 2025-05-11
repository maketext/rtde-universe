import rtde
import time

rtde.init()
time.sleep(1)
rtde.setInt3([1, 2, 3])
time.sleep(1)
rtde.pause()
time.sleep(1)
rtde.stop()
time.sleep(1)