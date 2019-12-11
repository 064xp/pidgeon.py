#!/usr/bin/env python3
import requests
import os
from pathlib import Path
import json
import argparse
import re
from datetime import date, timedelta

source = ""
userDefinedSources = []

def main():
    args = parseArgs()
    dir = str(Path.home()) + "/wallpaper"
    path = dir + "/wallpaper.jpg"

    if isFirstLaunch(dir):
        print("First time running, do you want to install? Y/n")
        choice = input()
        if choice == '' or choice.upper()[0] == 'Y':
            install(dir)
        else:
            exit(1)

    if args.config:
        pass

    loadConfigs(dir)


    url = getCorrespondingUrl()
    image = requests.get(url, stream=True)

    if image.status_code == 200:
        with open(path, "wb") as f:
            try:
                f.write(image.content)
            finally:
                f.close()


def loadConfigs(dir):
    global source
    global userDefinedSources
    configs = ""
    with open(dir + "/config.json", "r") as f:
        try:
            configs = f.read()
        finally:
            f.close()
    configs = json.loads(configs)
    source = configs["source"]
    userDefinedSources = configs["userDefinedSources"]

def isFirstLaunch(dir): #checks if its the first time script is launched
    if not os.path.isdir(dir) or not os.path.isfile(dir+'/config.json'):
        return True
    else:
        return False

def install(dir):
    configFilePath = dir + "/config.json"
    defaultConfig = {
    "source": "bing",
    "userDefinedSources": []
    }
    jsonString = json.dumps(defaultConfig)

    #make directory
    os.mkdir(dir)
    #write default config
    with open(configFilePath, "w") as f:
        try:
            f.write(jsonString)
        finally:
            f.close()
    #copy script to dir
    os.system(f'cp ./pidgeon.py {dir}')

def getBingUrl():
    res = requests.get("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US");
    json = res.json()
    url = "https://www.bing.com" + json["images"][0]["url"]
    return url

def getNasaAPODUrl():
    isValidImage = False
    timeDelta = 0
    regex = r'<a href="(image/.*)"'

    while not isValidImage:
        imgDate = date.today() - timedelta(timeDelta)
        day = str(imgDate.day)
        month = str(imgDate.month)
        year = str(imgDate.year)[2:]
        day = day if len(day) != 1 else '0' + day
        month = month if len(month) != 1 else '0' + month

        url = 'https://apod.nasa.gov/apod/ap' + year + month + day + '.html'
        try:
            res = requests.get(url)
        except:
            print("Could not fetch image")
            exit(1)


        html = res.text
        match = re.search(regex, html, re.IGNORECASE)

        if match:
            imgURL = 'https://apod.nasa.gov/apod/' + match.group(1)
            isValidImage = True
        else:
            isValidImage = False
            timeDelta += 1

    return imgURL



def getCorrespondingUrl():
    global source
    defaultSources = {
        "bing": getBingUrl,
        "nasa_apod": getNasaAPODUrl
    }

    if source in defaultSources:
        return defaultSources[source]()
    else:
        return userDefinedSources[source]


def parseArgs():
	parser = argparse.ArgumentParser(description='Fetch a brand new wallpaper everyday')
	parser.add_argument('-c','--config', action='store_true', help='Configuration, add sources, how ofter to change.')
	args = parser.parse_args()
	return args

if __name__ == "__main__":
    main()
