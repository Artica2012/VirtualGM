import asyncio
import logging
import time
from collections import OrderedDict
from pympler import asizeof


class AsyncCache:
    def __init__(self, capacity: int = 128, ttl: int = 120, max_size: int = None):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl
        self.max_size = max_size * 1000000

    def ac_cache(self, func):
        async def wrapper_func(*args, **kwargs):
            try:
                hashed_args = self.get_hash(func.__name__, args, kwargs)

                if hashed_args in self.cache:
                    # print("In Cache")
                    if (time.time() - self.cache[hashed_args]["TS"]) > self.ttl:
                        # print("Expired Entry")
                        output = await func(*args, **kwargs)
                        self.cache[hashed_args] = {"TS": time.time(), "output": output}
                    else:
                        output = self.cache[hashed_args]["output"]
                else:
                    # print("Not in Cache")
                    output = await func(*args, **kwargs)
                    self.cache[hashed_args] = {"TS": time.time(), "output": output}

                self.cache.move_to_end(hashed_args)
                self.cleanup()
                return output
            except Exception as e:
                logging.error(f"Async Cache Error: {e}, {func.__name__}")
                return await func(*args, **kwargs)

        return wrapper_func

    def get_hash(self, name, args, kwargs):
        return hash(f"{args[0].guild.id}{name}{args[1:]}{kwargs}")

    def cleanup(self):
        if self.max_size is not None:
            # print(self.max_size)
            # print(asizeof.asizeof(self.cache))
            while asizeof.asizeof(self.cache) >= self.max_size:
                # print("Size Reduced")
                self.cache.popitem(last=False)
        else:
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def timeoutClean(self):
        del_list = []
        for key in self.cache.keys():
            if (time.time() - self.cache[key]["TS"]) > self.ttl:
                del_list.append(key)

        for item in del_list:
            del self.cache[item]

    async def clean_loop(self, delay):
        while True:
            self.timeoutClean()
            print("Cache Cleaned")
            await asyncio.sleep(delay)


Cache = AsyncCache(ttl=60, max_size=256)
