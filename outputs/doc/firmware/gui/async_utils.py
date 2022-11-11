import uasyncio as asyncio
import lvgl as lv

class Lv_Async:
    def __init__(self, refresh_func=None, refresh_rate=20):
        self.refresh_func = refresh_func
        self.refresh_rate = refresh_rate
        self.refresh_event = asyncio.Event()
        self.refresh_task = asyncio.create_task(self.refresh())
        self.timer_task = asyncio.create_task(self.timer())

    async def refresh(self):
        while True:
            await self.refresh_event.wait()
            self.refresh_event.clear()
            lv.task_handler() 
            if self.refresh_func: self.refresh_func()

    async def timer(self):
        while True:
            await asyncio.sleep_ms(self.refresh_rate)
            lv.tick_inc(self.refresh_rate)
            self.refresh_event.set()