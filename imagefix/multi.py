#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import multiprocessing
import pprint
import random
import time


def busy_function(arg):
    sleep_int = random.randint(10, 20)
    time.sleep(sleep_int)
    print("Finishing {}".format(arg))
    return arg * sleep_int


def main():
    pool = multiprocessing.Pool(processes=4)

    # Call the parallel function with different inputs.
    args = range(1, 20)

    # Use map - blocks until all processes are done.
    result = pool.map(busy_function, args)
    pprint.pprint(result)


if __name__ == "__main__":
    main()
