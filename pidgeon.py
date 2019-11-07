import requests
import os
from pathlib import Path
import json

def main():
    dir = str(Path.home()) + "/wallpaper"
    path = dir + "/wallpaper.jpg"
    checkAndMakeDir(dir)
    url = getBingUrl()
    image = requests.get(url, stream=True)
    if image.status_code is 200:
        with open(path, "wb") as f:
            f.write(image.content)

def checkAndMakeDir(path):
    if not os.path.isdir(path):
        os.mkdir(path)

def getBingUrl():
    res = requests.get("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US");
    json = res.json()
    url = "https://www.bing.com" + json["images"][0]["url"]
    return url

if __name__ == "__main__":
    main()
