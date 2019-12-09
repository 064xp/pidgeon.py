import requests
import os
from pathlib import Path
import json
import argparse

sourceUrl = ""
userDefinedSources = []

def main():
    args = parseArgs()
    dir = str(Path.home()) + "/wallpaper"
    path = dir + "/wallpaper.jpg"
    url = getBingUrl()
    image = requests.get(url, stream=True)

    if isFirstLaunch(dir):
        install(dir)


    if args.config:
        pass

    loadConfigs(dir)

    if image.status_code is 200:
        with open(path, "wb") as f:
            try:
                f.write(image.content)
            finally:
                f.close()


def loadConfigs(dir):
    global sourceUrl
    global userDefinedSources
    configs = ""
    with open(dir + "/config.json", "r") as f:
        try:
            configs = f.read()
        finally:
            f.close()
    configs = json.loads(configs)
    sourceUrl = configs["source"]
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

def parseArgs():
	parser = argparse.ArgumentParser(description='Fetch a brand new wallpaper everyday')
	parser.add_argument('-c','--config', action='store_true', help='Configuration, add sources, how ofter to change.')
	args = parser.parse_args()
	return args

if __name__ == "__main__":
    main()
