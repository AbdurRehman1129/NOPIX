import os
import re
import sys
import json
import anyio
import httpx
import random
import argparse
import asyncio
import platform
import aiofiles
import aiofiles.ospath
import python_socks
from urllib.parse import unquote, parse_qs
from colorama import init, Fore, Style
from datetime import datetime
from models import *
from fake_useragent import UserAgent
from httpx_socks import AsyncProxyTransport

init(autoreset=True)
red = Fore.LIGHTRED_EX
blue = Fore.LIGHTBLUE_EX
green = Fore.LIGHTGREEN_EX
yellow = Fore.LIGHTYELLOW_EX
black = Fore.LIGHTBLACK_EX
white = Fore.LIGHTWHITE_EX
reset = Style.RESET_ALL
magenta = Fore.LIGHTMAGENTA_EX
proxy_file = "proxies.txt"
log_file = "http.log"


class Config:
    def __init__(
        self,
        colors,
        countdown,
        start_param,
        auto_upgrade,
        swtime,
        ewtime,
        disable_log,
    ):
        self.colors = colors
        self.countdown = countdown
        self.start_param = start_param
        self.auto_upgrade = auto_upgrade
        self.swtime = swtime
        self.ewtime = ewtime
        self.disable_log = disable_log


class NotPixTod:
    def __init__(self, no, config, proxies):
        ci = lambda a, b: (b * 1000) + (a + 1)
        self.cfg: Config = config
        self.p = no
        self.proxies = proxies
        if len(proxies) > 0:
            proxy = self.get_random_proxy(no)
            transport = AsyncProxyTransport.from_url(proxy)
            self.ses = httpx.AsyncClient(transport=transport, timeout=1000)
        else:
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

    async def ipinfo(self):
        ipinfo1_url = "https://ipapi.co/json/"
        ipinfo2_url = "https://ipwho.is/"
        ipinfo3_url = "https://freeipapi.com/api/json"
        headers = {"user-agent": "marin kitagawa"}
        try:
            res = await self.http(ipinfo1_url, headers)
            ip = res.json().get("ip")
            country = res.json().get("country")
            if not ip:
                res = await self.http(ipinfo2_url, headers)
                ip = res.json().get("ip")
                country = res.json().get("country_code")
                if not ip:
                    res = await self.http(ipinfo3_url, headers)
                    ip = res.json().get("ipAddress")
                    country = res.json().get("countryCode")
            self.log(f"{green}ip : {white}{ip} {green}country : {white}{country}")
        except json.decoder.JSONDecodeError:
            self.log(f"{green}ip : {white}None {green}country : {white}None")

    def get_random_proxy(self, isself, israndom=False):
        if israndom:
            return random.choice(self.proxies)
        return self.proxies[isself % len(self.proxies)]

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
                    async with aiofiles.open(log_file,
                                            "a",
                                            encoding="utf-8") as hw:
                        await hw.write(f"{res.status_code} {res.text}\n")
                if not res.is_success:
                    self.log(
                        f"{yellow}failed get json response !, code : {res.status_code}"
                    )
                    await countdown(3)
                    continue

                return res
            except (
                httpx.ProxyError,
                python_socks._errors.ProxyTimeoutError,
                python_socks._errors.ProxyError,
                python_socks._errors.ProxyConnectionError,
            ):
                proxy = self.get_random_proxy(0, israndom=True)
                transport = AsyncProxyTransport.from_url(proxy)
                self.ses = httpx.AsyncClient(transport=transport)
                self.log(f"{yellow}proxy error,selecting random proxy !")
                await asyncio.sleep(3)
                continue
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

    async def start(self, query_id):
        proxy = None
        if len(self.proxies) > 0:
            unique = random.randint(0, len(self.proxies) - 1)
            proxy = self.proxies[unique]
            await self.ipinfo()

        query = query_id

        marin = lambda data: {
            key: value[0]
            for key, value in parse_qs(data).items()
        }
        parser = marin(query_id)
        user_str = parser.get("user")

        if user_str is None:
            self.log(
                f"{red}Error: Could not extract user information from query ID. Skipping session."
            )
            return

        try:
            user = json.loads(user_str)
        except json.JSONDecodeError:
            self.log(
                f"{red}Error: Invalid JSON format in user data. Skipping session."
            )
            return

        uid = str(user.get("id"))
        res = await get_by_id(uid)
        if res is None:
            first_name = user.get("first_name")
            await insert(uid, first_name)
            ua = UserAgent().random
            await update_useragent(uid, ua)
            res = await get_by_id(uid)

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
            try:
                res_json = res.json()
            except json.decoder.JSONDecodeError:
                self.log(f"{yellow}failed to decode json response !")
                await countdown(3)
                continue

            balance = int(res_json.get("userBalance", 0))
            await update_balance(uid, balance)
            self.log(f"{green}account balance : {white}{balance}")
            if "charges" not in res_json:
                self.log(f"{yellow}charges key not found in json response !")
                await countdown(3)
                continue

            charges = res_json.get("charges") // 2
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


def get_sessions():
    if not os.path.exists("data.txt"):
        return []
    with open("data.txt", "r") as f:
        sessions = f.read().splitlines()
    return sessions


def get_datas(proxy_file):
    if not os.path.exists(proxy_file):
        open(proxy_file, "a")
    proxies = open(proxy_file).read().splitlines()
    return proxies


async def bound(sem, data, query_id):
    async with sem:
        return await NotPixTod(*data).start(query_id)


async def main():
    await initdb()
    arg = argparse.ArgumentParser()
    arg.add_argument("--proxy",
                        "-P",
                        default=proxy_file,
                        help=
                        f"Perform custom input for proxy files (default : {proxy_file})"
                        )
    arg.add_argument(
        "--action",
        "-A",
        help="Function to directly enter the menu without displaying input",
    )
    arg.add_argument(
        "--worker",
        "-W",
        help=
        "Total workers or number of threads to be used (default : cpu core / 2)",
    )
    arg.add_argument("--marin", action="store_true")
    arg.add_argument("--disable-log", action="store_true")
    args = arg.parse_args()
    disable_log = args.disable_log
    async with aiofiles.open("config.json") as r:
        read = await r.read()
        cfg = json.loads(read)
        config = Config(colors=cfg.get("colors"),
                        countdown=cfg.get("countdown"),
                        start_param=cfg.get("referral_code"),
                        auto_upgrade=cfg.get("auto_upgrade"),
                        swtime=cfg.get("time_before_start", [30, 60])[0],
                        ewtime=cfg.get("time_before_start", [30, 60])[1],
                        disable_log=disable_log)
    banner = f"""
{magenta}┏┓┳┓┏┓  ┏┓   •       {white}NotPixTod Auto Claim for {green}N*t P*xel
{magenta}┗┓┃┃┗┓  ┃┃┏┓┏┓┓┏┓┏╋  {green}Author : {white}[redacted]
{magenta}┗┛┻┛┗┛  ┣┛┛ ┗┛┃┗ ┗┗  {green}Note : {white}Every Action Has a Consequence
{magenta}        ┛     
    """
    main_menu = f"""
    {white}1{green}. {white}Add/Create Session 
    {white}2{green}. {white}Start Bot (Multi Process)
    {white}3{green}. {white}Start Bot (Single Process)
    """
    sessions = get_sessions()
    proxies = get_datas(proxy_file=args.proxy)
    your_data = f"""
{white}Total session : {green}{len(sessions)}
{white}Total proxy : {green}{len(proxies)}
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
            query_id = input(
                f"{white}[{yellow}?{white}] {yellow}Input Query ID : {reset}"
            )
            marin = lambda data: {
                key: value[0]
                for key, value in parse_qs(data).items()
            }
            parser = marin(query_id)
            user_str = parser.get("user")

            if user_str is None:
                self.log(
                    f"{red}Error: Could not extract user information from query ID. Skipping session."
                )
                continue

            try:
                user = json.loads(user_str)
            except json.JSONDecodeError:
                self.log(
                    f"{red}Error: Invalid JSON format in user data. Skipping session."
                )
                continue

            uid = str(user.get("id"))
            first_name = user.get("first_name")

            existing_user = await get_by_id(uid)
            if existing_user is None:
                await insert(uid, first_name)
                ua = UserAgent().random
                await update_useragent(uid, ua)
                self.log(f"{green}Session added for user: {white}{first_name}")

                with open("data.txt", "a") as f:
                    f.write(query_id + "\n")

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
                sessions = get_sessions()
                proxies = get_datas(proxy_file=args.proxy)
                tasks = []
                for no, query_id in enumerate(sessions):
                    tasks.append(
                        asyncio.create_task(
                            bound(sema, (no, config, proxies), query_id)))
                result = await asyncio.gather(*tasks)
                await countdown(config.countdown)
        elif option == "3":
            while True:
                sessions = get_sessions()
                proxies = get_datas(proxy_file=args.proxy)
                for no, query_id in enumerate(sessions):
                    await NotPixTod(no=no, config=config,
                                    proxies=proxies).start(query_id=query_id)
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
