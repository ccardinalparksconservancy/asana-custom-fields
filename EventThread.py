import threading
from random import randint
import time


#### threading class ####
class EventThread(threading.Thread):
    def __init__(self, val):
        threading.Thread.__init__(self)
        self.val = val

    def run(self):
        for i in range(1, self.val):
            print('Value %d in thread %s' % (i, self.getName()))
 
            # Sleep for random time between 1 ~ 3 second
            secondsToSleep = randint(1, 5)
            print('%s sleeping for %d seconds...' % (self.getName(), secondsToSleep))
            time.sleep(secondsToSleep)

t1 = EventThread(4)
t1.setName('Thread1')
t2 = EventThread(8)
t2.setName('Thread2')
t1.start()
t2.start()
t1.join()
t2.join()

print('Threads terminated!')