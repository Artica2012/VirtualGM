import time
from collections import OrderedDict


class AsyncCache:
    def __init__(self, capacity: int, ttl: int):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl

    def ac_cache(self, func):
        async def wrapper_func(*args, **kwargs):
            hashed_args = hash(f"{args[0].guild.id}{func.__name__}{kwargs}")
            if hashed_args in self.cache:
                if (time.time() - self.cache[hashed_args]["TS"]) > self.ttl:
                    output = await func(*args, **kwargs)

                    self.cache[hashed_args] = {"TS": time.time(), "output": output}

                else:
                    output = self.cache[hashed_args]["output"]
            else:
                output = await func(*args, **kwargs)
                self.cache[hashed_args] = {"TS": time.time(), "output": output}

            self.cache.move_to_end(hashed_args)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

            return output

        return wrapper_func


cache = AsyncCache(capacity=128, ttl=60)
