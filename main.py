#!/usr/bin/env python

from __future__ import annotations
import websockets

from datetime import datetime, timezone
from dotenv import load_dotenv

import time
from urllib import parse
import aiohttp
import base64
import time
import json
import contextlib
import os
import asyncio
import discord
from discord.ext import commands, tasks
from os.path import exists

import matplotlib.pyplot as plt
import numpy as np
from math import sin, cos, radians

class FailedToConnect(Exception):
    pass
class InvalidRequest(Exception):
    def __init__(self, *args, code=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = code
class InvalidAttributeCombination(Exception):
    pass


class Auth:
    """ Holds the authentication information """

    @staticmethod
    def get_basic_token(email: str, password: str) -> str:
        return base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("utf-8")

    def __init__(
            self,
            email: str = None,
            password: str = None,
            token: str = None,
            appid: str = None,
            creds_path: str = None,
            cachetime: int = 120,
            max_connect_retries: int = 1,
            session: aiohttp.ClientSession() = None,
            refresh_session_period: int = 180,
            item_id: str = "",
    ):
        self.session: aiohttp.ClientSession() = session or aiohttp.ClientSession()
        self.max_connect_retries: int = max_connect_retries
        self.refresh_session_period: int = refresh_session_period

        self.token: str = token or Auth.get_basic_token(email, password)
        self.creds_path: str = creds_path or f"{os.getcwd()}/creds/{self.token}.json"
        self.appid: str = appid or 'e3d5ea9e-50bd-43b7-88bf-39794f4e3d40'
        self.sessionid: str = ""
        self.key: str = ""
        self.new_key: str = ""
        self.spaceid: str = ""
        self.spaceids: dict[str: str] = {
            "uplay": "0d2ae42d-4c27-4cb7-af6c-2099062302bb",
            "psn": "0d2ae42d-4c27-4cb7-af6c-2099062302bb",
            "xbl": "0d2ae42d-4c27-4cb7-af6c-2099062302bb"
        }
        self.profileid: str = ""
        self.userid: str = ""
        self.expiration: str = ""
        self.new_expiration: str = ""

        self.cachetime: int = cachetime
        self.cache = {}

        self._login_cooldown: int = 0
        self._session_start: float = time.time()

    async def _ensure_session_valid(self) -> None:
        if not self.session:
            await self.refresh_session()
        elif 0 <= self.refresh_session_period <= (time.time() - self._session_start):
            await self.refresh_session()

    async def refresh_session(self) -> None:
        """ Closes the current session and opens a new one """
        if self.session:
            try:
                await self.session.close()
            except:
                pass

        self.session = aiohttp.ClientSession()
        self._session_start = time.time()

    async def get_session(self) -> aiohttp.ClientSession():
        """ Retrieves the current session, ensuring it's valid first """
        await self._ensure_session_valid()
        return self.session

    def save_creds(self) -> None:
        """ Saves the credentials to a file """

        if not os.path.exists(os.path.dirname(self.creds_path)):
            os.makedirs(os.path.dirname(self.creds_path))

        if not os.path.exists(self.creds_path):
            with open(self.creds_path, 'w') as f:
                json.dump({}, f)

        # write to file, overwriting the old one
        with open(self.creds_path, 'w') as f:
            json.dump({
                "sessionid": self.sessionid,
                "key": self.key,
                "new_key": self.new_key,
                "spaceid": self.spaceid,
                "profileid": self.profileid,
                "userid": self.userid,
                "expiration": self.expiration,
                "new_expiration": self.new_expiration,
            }, f, indent=4)

    def load_creds(self) -> None:
        """ Loads the credentials from a file """

        if not os.path.exists(self.creds_path):
            return

        with open(self.creds_path, "r") as f:
            data = json.load(f)

        self.sessionid = data.get("sessionid", "")
        self.key = data.get("key", "")
        self.new_key = data.get("new_key", "")
        self.spaceid = data.get("spaceid", "")
        self.profileid = data.get("profileid", "")
        self.userid = data.get("userid", "")
        self.expiration = data.get("expiration", "")
        self.new_expiration = data.get("new_expiration", "")

        self._login_cooldown = 0

    async def connect(self, _new: bool = False) -> None:
        """ Connect to Ubisoft, automatically called when needed """
        self.load_creds()

        if self._login_cooldown > time.time():
            raise FailedToConnect("Login on cooldown")

        # If keys are still valid, don't connect again
        if _new:
            if self.new_key and datetime.fromisoformat(self.new_expiration[:26]+"+00:00") > datetime.now(timezone.utc):
                return
        else:
            if self.key and datetime.fromisoformat(self.expiration[:26]+"+00:00") > datetime.now(timezone.utc):
                await self.connect(_new=True)
                return

        session = await self.get_session()
        headers = {
            "User-Agent": "UbiServices_SDK_2020.Release.58_PC64_ansi_static",
            "Content-Type": "application/json; charset=UTF-8",
            "Ubi-AppId": self.appid,
            "Authorization": "Basic " + self.token
        }

        if _new:
            headers["Ubi-AppId"] = self.appid
            headers["Authorization"] = "Ubi_v1 t=" + self.key

        resp = await session.post(
            url="https://public-ubiservices.ubi.com/v3/profiles/sessions",
            headers=headers,
            data=json.dumps({"rememberMe": True})
        )

        data = await resp.json()

        if "ticket" in data:
            if _new:
                self.new_key = data.get('ticket')
                self.new_expiration = data.get('expiration')
            else:
                self.key = data.get("ticket")
                self.expiration = data.get("expiration")
            self.profileid = data.get('profileId')
            self.sessionid = data.get("sessionId")
            self.spaceid = data.get("spaceId")
            self.userid = data.get("userId")
        else:
            message = "Unknown Error"
            if "message" in data and "httpCode" in data:
                message = f"HTTP {data['httpCode']}: {data['message']}"
            elif "message" in data:
                message = data["message"]
            elif "httpCode" in data:
                message = str(data["httpCode"])
            raise FailedToConnect(message)

        self.save_creds()
        await self.connect(_new=True)

    async def close(self) -> None:
        """ Closes the session associated with the auth object """
        self.save_creds()
        await self.session.close()

    async def get(self, *args, retries: int = 0, json_: bool = True, new: bool = False, **kwargs) -> dict | str:
        if (not self.key and not new) or (not self.new_key and new):
            last_error = None
            for _ in range(self.max_connect_retries):
                try:
                    await self.connect()
                    break
                except FailedToConnect as e:
                    last_error = e
            else:
                # assume this error is going uncaught, so we close the session
                await self.close()

                if last_error:
                    raise last_error
                else:
                    raise FailedToConnect("Unknown Error")

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        authorization = kwargs["headers"].get("Authorization") or "Ubi_v1 t=" + (self.new_key if new else self.key)
        appid = kwargs["headers"].get("Ubi-AppId") or self.appid

        kwargs["headers"]["Authorization"] = authorization
        kwargs["headers"]["Ubi-AppId"] = appid
        kwargs["headers"]["Ubi-LocaleCode"] = kwargs["headers"].get("Ubi-LocaleCode") or "en-US"
        kwargs["headers"]["Ubi-SessionId"] = kwargs["headers"].get("Ubi-SessionId") or self.sessionid
        kwargs["headers"]["User-Agent"] = kwargs["headers"].get("User-Agent") or "UbiServices_SDK_2020.Release.58_PC64_ansi_static"
        kwargs["headers"]["Connection"] = kwargs["headers"].get("Connection") or "keep-alive"
        kwargs["headers"]["expiration"] = kwargs["headers"].get("expiration") or self.expiration

        session = await self.get_session()
        resp = await session.get(*args, **kwargs)

        if json_:
            try:
                data = await resp.json()
            except Exception:
                text = await resp.text()
                message = text.split("h1>")
                message = message[1][:-2] if len(message) > 1 else text
                raise InvalidRequest(f"Received a text response, expected JSON response. Message: {message}")

            if "httpCode" in data:
                if data["httpCode"] == 401:
                    if retries >= self.max_connect_retries:
                        # wait 30 seconds before sending another request
                        self._login_cooldown = time.time() + 30

                    # key no longer works, so remove key and let the following .get() call refresh it
                    self.key = None
                    return await self.get(*args, retries=retries + 1, **kwargs)
                else:
                    msg = data.get("message", "")
                    if data["httpCode"] == 404:
                        msg = f"Missing resource {data.get('resource', args[0])}"
                    raise InvalidRequest(f"HTTP {data['httpCode']}: {msg}", code=data["httpCode"])

            return data
        else:
            return await resp.text()

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='.', intents=intents)

@client.event
async def on_ready():
    print(f"Connected at {time.time()}s!")

    read_ws.start()



@tasks.loop(minutes=105)
async def read_ws():
    auth = Auth(os.environ["AUTH_EMAIL"] or os.getenv("AUTH_EMAIL"), os.environ["AUTH_PW"] or os.getenv("AUTH_PW"))
    start = time.time()

    print("Starting WS...")

    await auth.connect()
    
    headers = {
        "Ubi-SessionId": auth.sessionid,
        "Authorization": "Ubi_v1 t=" + auth.key,
        "Ubi-AppId": "e3d5ea9e-50bd-43b7-88bf-39794f4e3d40"
    }

    async with websockets.connect("wss://public-ws-ubiservices.ubi.com/v2/websocket?spaceIds=45d58365-547f-4b45-ab5b-53ed14cc79ed&notificationTypes=BLOCKLIST_ADD", extra_headers=headers) as websocket:
        
        debug = False

        while (time.time() - start) < 6300:
            profile = {
                "linked": []
            }
            raw_data = None
            try:
                raw_data = await asyncio.wait_for(websocket.recv(), timeout=(6300 - (time.time() - start)))
            except TimeoutError:
                print("Login expired, refreshing.")
                break
                                              
            if debug:
                print(f"Received!")

            data = json.loads(raw_data)

            profile['profile_id'] = data['content']['blockedProfileId']

            if debug:
                print(json.dumps(data, indent=3))
                print("Profile ID: " + profile['profile_id'])

            player = await auth.get(f"https://public-ubiservices.ubi.com/v1/profiles/{profile['profile_id']}")
            persona = await auth.get(f"https://public-ubiservices.ubi.com/v1/profiles/persona?profileIds={profile['profile_id']}&spaceId=0d2ae42d-4c27-4cb7-af6c-2099062302bb")
            stats = await auth.get(f"https://public-ubiservices.ubi.com/v2/spaces/0d2ae42d-4c27-4cb7-af6c-2099062302bb/title/r6s/skill/full_profiles?profile_ids={profile['profile_id']}&platform_families=pc")
            profiles = await auth.get(f"https://public-ubiservices.ubi.com/v3/users/{profile['profile_id']}/profiles")
   
            if debug:
                print("Player:")
                print(json.dumps(player, indent=3))
                print("Persona:")
                print(json.dumps(persona, indent=3))
                print("Stats:")
                print(json.dumps(stats, indent=3))
                print("Profiles:")
                print(json.dumps(profiles, indent=3))

            for platform in profiles["profiles"]:
                match platform['platformType']:
                    case "uplay":
                        profile['linked'].append(f"**Uplay**:\n\tLink: https://r6.tracker.network/r6/search?name={profile['profile_id']}&platform=4")
                    case "steam":
                        profile['linked'].append(f"**Steam**:\n\tLink: https://findsteamid.com/steamid/{platform['idOnPlatform']}")
                    case "xbl":
                        profile['linked'].append(f"**XBL**:\n\tLink: https://xboxgamertag.com/search/{platform['nameOnPlatform']}")
                    case "twitch":
                        profile['linked'].append(f"**Twitch**:\n\tLink: https://www.twitch.tv/{platform['nameOnPlatform']}")
                    case _:
                        # OCD
                        upper_first = list(platform['platformType'])
                        upper_first[0] = upper_first[0].upper()
                        upper_first = ''.join(upper_first)

                        profile['linked'].append(f"**{upper_first}**:\n\tName: **{platform['nameOnPlatform']}**\n\tID: **{platform['idOnPlatform']}**")
            
            profile['uplay'] = player['nameOnPlatform']
            profile['nickname'] = persona['personas'][0]['nickname'] if (persona['personas'] and persona['personas'][0]['obj']['Enabled']) else "Offline/No Nickname"
            
            ranked_board = next((item for item in stats['platform_families_full_profiles'][0]['board_ids_full_profiles'] if item['board_id'] == "ranked"), None)['full_profiles'][0]
            profile['peak_mmr'] = ranked_board['profile']['max_rank_points']
            profile['mmr'] = ranked_board['profile']['rank_points']
            profile['kills'] = ranked_board['season_statistics']['kills']
            profile['deaths'] = ranked_board['season_statistics']['deaths']
            profile['wins'] = ranked_board['season_statistics']['match_outcomes']['wins']
            profile['losses'] = ranked_board['season_statistics']['match_outcomes']['losses']
            profile['kd'] = round((profile['kills'] + 1) / (profile['deaths'] + 1), 2)
            profile['wl'] = round((profile['wins'] + 1) / (profile['losses'] + 1 + profile['wins'] + 1) * 100, 2)

            if debug:
                print(json.dumps(ranked_board, indent=3))

            print(f"Blocked {profile['uplay']} ({profile['nickname']})\n")
            print(f"Rank: {profile['mmr']} ({profile['peak_mmr']})")
            print(f"KD: {profile['kd']} ({profile['kills']} kills - {profile['deaths']} deaths)")
            print(f"WL: {profile['wl']} ({profile['wins']} wins - {profile['losses']} losses)")
            print(f"R6 Tracker: https://r6.tracker.network/profile/pc/{profile['profile_id']}\n\n\n")

            await client.wait_until_ready()

            msg = f"\n## Player:\n\tUplay: **{profile['uplay']}**\n\tNickname: **{profile['nickname']}**"
            msg += f"\n### Rank:\n\tCurrent: **{profile['mmr']}**\n\tPeak: **{profile['peak_mmr']}**)"
            msg += f"\n### Stats:\n\tKD: **{profile['kd']}**\n\tKills: **{profile['kills']}**\n\tDeaths: **{profile['deaths']}**\n\n\tWL: **{profile['wl']}**\n\tWins: **{profile['wins']}**\n\tLosses: **{profile['losses']}**"
           
            profiles_str = '\n'.join(profile['linked'])
            msg += f"\n### Linked Accounts:\n{profiles_str}"

            embed=discord.Embed(title=f'Blocked Player (@wydbolt)', description=f'{msg}', color=0xFF5733)
            embed.set_thumbnail(url=f"https://ubisoft-avatars.akamaized.net/{profile['profile_id']}/default_tall.png")
            
            await client.get_channel(int(os.environ["CHANNEL_ID"] or os.getenv("CHANNEL_ID"))).send(embed=embed)
        
        print("Terminating WS stream...")
        await websocket.close()

    print("Finalizing auth session, opening new stream shortly...")
    await auth.close()
client.run(os.environ["TOKEN"])