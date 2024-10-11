import asyncio
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

import aiofiles
import aiofiles.ospath
import httpx
from colorama import Fore, Style, init
from fake_useragent import UserAgent

init(autoreset=True)
red = Fore.LIGHTRED_EX
blue = Fore.LIGHTBLUE_EX
green = Fore.LIGHTGREEN_EX
yellow = Fore.LIGHTYELLOW_EX
black = Fore.LIGHTBLACK_EX
white = Fore.LIGHTWHITE_EX
reset = Style.RESET_ALL
magenta = Fore.LIGHTMAGENTA_EX

log_file = "http.log"


class Config:
    def __init__(
        self,
        colors,
        countdown,
        auto_upgrade,
        swtime,
        ewtime,
        disable_log,
    ):
        self.colors = colors
        self.countdown = countdown
        self.auto_upgrade = auto_upgrade
        self.swtime = swtime
        self.ewtime = ewtime
        self.disable_log = disable_log


class NotPixTod:
    def __init__(self, no, config):
        ci = lambda a, b: (b * 1000) + (a + 1)
        self.cfg: Config = config
        self.p = no
        self.ses = httpx.AsyncClient(timeout=1000)
        self.colors = [
            "#3690ea",
            "#e46e6e",
            "#ffffff",
            "#be0039",
            "#6d001a",
            "#ffd635",
            "#ff9600",
            "#bf4300",
            "#7eed56",
            "#00cc78",
            "#00a368",
        ]
        self.block = [
            {
                "color": "#3690EA",
                "block": [[ci(245, x), ci(311, x)] for x in range(547, 592, 1)],
            },
            {
                "color": "#3690EA",
                "block": [[ci(243, x), ci(296, x)] for x in range(461, 515, 1)]
            },
            {
                "color": "#3690EA",
                "block": [[ci(704, x), ci(755, x)] for x in range(659, 684, 1)]
            }
        ]

    def log(self, msg):
        now = datetime.now().isoformat().split("T")[1].split(".")[0]
        print(
            f"{black}[{now}]{white}-{blue}[{white}acc {self.p + 1}{blue}]{white} {msg}{reset}"
        )

    async def http(self, url, headers, data=None):
        while True:
            try:
                if not self.cfg.disable_log:
                    if not await aiofiles.ospath.exists(log_file):
                        async with aiofiles.open(log_file, "w") as w:
                            await w.write("")
                    logsize = await aiofiles.ospath.getsize(log_file)
                    if logsize / 1024 / 1024 > 1:
                        async with aiofiles.open(log_file, "w") as w:
                            await w.write("")
                if data is None:
                    res = await self.ses.get(url, headers=headers)
                elif data == "":
                    res = await self.ses.post(url, headers=headers)
                else:
                    res = await self.ses.post(url, headers=headers, data=data)
                if not self.cfg.disable_log:
                    async with aiofiles.open(log_file, "a", encoding="utf-8") as hw:
                        await hw.write(f"{res.status_code} {res.text}\n")
                if "<title>" in res.text or res.text[0] != "{":
                    self.log(f"{yellow}failed get json response !")
                    await countdown(3)
                    continue

                return res
            except httpx.NetworkError:
                self.log(f"{yellow}network error !")
                await asyncio.sleep(3)
                continue
            except httpx.TimeoutException:
                self.log(f"{yellow}connection timeout !")
                await asyncio.sleep(3)
                continue
            except httpx.RemoteProtocolError:
                self.log(f"{yellow}connection close without response !")
                await asyncio.sleep(3)
                continue
            except Exception as e:
                self.log(f"{yellow}{e}")
                await asyncio.sleep(3)
                continue

    async def start(self, query):
        if query is None:
            return

        marin = lambda data: {key: value[0] for key, value in parse_qs(data).items()}
        parser = marin(query)
        user = parser.get("user")
        uid = re.search(r'id":(.*?),', user).group(1)
        res = await get_by_id(uid)
        if res is None:
            self.log(f"{red}user {uid} not found in database, please create session first !")
            return
        useragent = res.get("useragent")
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"initData {query}",
            "user-agent": useragent,
            "origin": "https://app.notpx.app",
            "x-requested-with": "org.telegram.messenger",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://app.notpx.app/",
            "accept-language": "en,id-ID;q=0.9,id;q=0.8,en-US;q=0.7",
        }
        me_url = "https://notpx.app/api/v1/users/me"
        status_url = "https://notpx.app/api/v1/mining/status"
        paint_url = "https://notpx.app/api/v1/repaint/start"
        claim_url = "https://notpx.app/api/v1/mining/claim"
        boost_buy_url = "https://notpx.app/api/v1/mining/boost/check/"
        boosts = ["energyLimit", "paintReward", "reChargeSpeed"]
        res = await self.http(me_url, headers)
        while True:
            res = await self.http(status_url, headers)
            balance = int(res.json().get("userBalance", 0))
            await update_balance(uid, balance)
            self.log(f"{green}account balance : {white}{balance}")
            charges = res.json().get("charges") // 2
            if charges <= 0:
                break
            for i in range(charges):
                pixel_id = random.randint(1, 1000000)
                choice = random.choice(self.block)
                block = choice.get("block")
                color = choice.get("color").upper()
                temp_color = [color.upper() for color in self.colors]
                temp_color.remove(color)
                first_color = random.choice(temp_color).upper()
                pixel_id = random.choice(random.choice(block))
                for i in range(2):
                    if i == 0:
                        data = {"pixelId": pixel_id, "newColor": first_color}
                    else:
                        data = {"pixelId": pixel_id, "newColor": color}
                    res = await self.http(paint_url, headers, json.dumps(data))
                    if res.status_code != 200:
                        self.log(f"failed paint pixel id : {white}{pixel_id}")
                        continue
                    new_balance = int(res.json().get("balance"))
inc = new_balance - balance
                    balance = new_balance
                    self.log(
                        f"{green}success paint id : {white}{pixel_id}{green},{white}reward {green}+{inc}"
                    )
                await countdown(3)
            res = await self.http(claim_url, headers)
            if res.status_code != 200:
                self.log(f"{yellow}failed claim mining !")
            else:
                claimed = res.json().get("claimed")
                self.log(f"{green}success claim mining, {white}{claimed}")
            for boost in boosts:
                buy_url = f"{boost_buy_url}{boost}"
                if self.cfg.auto_upgrade[boost]:
                    res = await self.http(buy_url, headers)
                    if res.status_code != 200:
                        self.log(f"{red}failed buy booster {white}{boost}")
                        continue
                    self.log(f"{green}success buy booster {white}{boost}")


def get_queries():
    if not os.path.exists("data.txt"):
        open("data.txt", "a")
    queries = open("data.txt").read().splitlines()
    return queries


async def bound(sem, data, query):
    async with sem:
        return await NotPixTod(*data).start(query)


async def main():
    await initdb()
    arg = argparse.ArgumentParser()
    arg.add_argument(
        "--action",
        "-A",
        help="Function to directly enter the menu without displaying input",
    )
    arg.add_argument(
        "--worker",
        "-W",
        help="Total workers or number of threads to be used (default : cpu core / 2)",
    )
    arg.add_argument("--marin", action="store_true")
    arg.add_argument("--disable-log", action="store_true")
    args = arg.parse_args()
    disable_log = args.disable_log
    async with aiofiles.open("config.json") as r:
        read = await r.read()
        cfg = json.loads(read)
        config = Config(
            colors=cfg.get("colors"),
            countdown=cfg.get("countdown"),
            auto_upgrade=cfg.get("auto_upgrade"),
            swtime=cfg.get("time_before_start", [30, 60])[0],
            ewtime=cfg.get("time_before_start", [30, 60])[1],
            disable_log=disable_log,
        )
    banner = f"""
{magenta}┏┓┳┓┏┓  ┏┓    •      {white}NotPixTod Auto Claim for {green}N*t P*xel
{magenta}┗┓┃┃┗┓  ┃┃┏┓┏┓┓┏┓┏╋  {green}Author : {white}[REDACTED]
{magenta}┗┛┻┛┗┛  ┣┛┛ ┗┛┃┗ ┗┗  {green}Note : {white}Every Action Has a Consequence
{magenta}              ┛      
        """
    main_menu = f"""
     {white}1{green}. {white}Add/Create Session 
     {white}2{green}. {white}Start Bot (Multi Process)
     {white}3{green}. {white}Start Bot (Single Process)
     """
    queries = get_queries()
    your_data = f"""
{white}Total initData : {green}{len(queries)}
        """
    while True:
        if not args.marin:
            os.system("cls" if os.name == "nt" else "clear")
        print(banner)
        print(your_data)
        if args.action:
            option = args.action
        else:
            print(main_menu)
            option = input(f"{white}[{yellow}?{white}] {yellow}input number : {reset}")
        if option == "1":
            query = input(
                f"{white}[{yellow}?{white}] {yellow}input initData : {reset}"
            )
            x = NotPixTod(no=0, config=config)
            marin = lambda data: {key: value[0] for key, value in parse_qs(data).items()}
            parser = marin(query)
            user = parser.get("user")
            uid = re.search(r'id":(.*?),', user).group(1)
            first_name = re.search(r'"first_name":"(.*?)"', user).group(1)
            res = await get_by_id(uid)
            if not res:
                await insert(uid, first_name)
                ua = UserAgent().random
                await update_useragent(uid, ua)
            input(f"{blue}press enter to continue !")
            continue
        elif option == "2":
            if args.worker:
                worker = int(args.worker)
            else:
                worker = int(os.cpu_count() / 2)
                if worker <= 0:
                    worker = 1
            sema = asyncio.Semaphore(worker)
            while True:
                queries = get_queries()
                tasks = [
                    asyncio.create_task(
                        bound(sema, (no, config), query)
                    )
                    for no, query in enumerate(queries)
                ]
                result = await asyncio.gather(*tasks)
                await countdown(config.countdown)
        elif option == "3":
            while True:
                queries = get_queries()
                for no, query in enumerate(queries):
                    await NotPixTod(no=no, config=config).start(
                        query=query
                    )
                await countdown(config.countdown)


async def countdown(t):
    for i in range(t, 0, -1):
        minute, seconds = divmod(i, 60)
        hour, minute = divmod(minute, 60)
        seconds = str(seconds).zfill(2)
        minute = str(minute).zfill(2)
        hour = str(hour).zfill(2)
        print(f"waiting for {hour}:{minute}:{seconds} ", flush=True, end="\r")
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit()
