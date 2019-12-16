#!/usr/bin/python3
# Example code for a good/healthy Threaded wait pattern

from random import random
import threading
import time

progress = 0
sleeper = 0
result = None
result_available = threading.Event()

def background_calculation():
    # here goes some long calculation
    global progress
    global sleeper
    for i in range(20):
        sleeper = random() * 3
        time.sleep( sleeper )
        progress = i + 1

    # when the calculation is done, the result is stored in a global variable
    global result
    result = 42
    result_available.set()

    # do some more work before exiting the thread
    time.sleep(10)

def main():
    thread = threading.Thread(target=background_calculation)
    thread.start()

    # wait here for the result to be available before continuing
    while not result_available.wait(timeout=5):
        #print('\r{}% done...'.format(progress), '\r{}secs sleeping...'.format(sleeper), end='', flush=True)
        print('\r{}% done...'.format(progress), 'sleeping {} seconds...'.format(sleeper), end='', flush=True)

    print('\r{}% done...'.format(progress))

    print('The result is', result)

if __name__ == '__main__':
    main()