import asyncio
import time
import string
import random
freq = 1

async def firstWorker():
    while True:
        await asyncio.sleep(1)
        s = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        asyncio.ensure_future(secondWorker(s))
        print("Main Thread")

async def secondWorker(name):
    while True:
        await asyncio.sleep(freq)
        print(f"Worker Executed {name}")


loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(firstWorker())
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    print("Closing Loop")
    loop.close()