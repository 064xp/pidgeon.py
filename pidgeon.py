#!/usr/bin/env python3
import requests
import os
from pathlib import Path
import json
import argparse
import subprocess
import re
from datetime import date, timedelta

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

chosenSource = ""
sources = [
    {
        'name': 'Bing Picture of the Day',
        'urlFunc': getBingUrl,
        'configName': 'bing',
        'url': ''
    },
    {
        'name': 'Nasa Astronomy Picture of the Day',
        'urlFunc': getNasaAPODUrl,
        'configName': 'nasa_apod',
        'url': ''
    }
]

def main():
    args = parseArgs()
    dir = str(Path.home()) + "/wallpaper"
    path = dir + "/wallpaper.jpg"


    if isFirstLaunch(dir):
        print("First time running, do you want to install? Y/n")
        wantsToInstall = yesNoPrompt()
        if wantsToInstall:
            install(dir)
        else:
            exit(0)

    if args.config:
        chooseSource(dir)

    loadConfigs(dir)

    url = getCorrespondingUrl()
    image = requests.get(url, stream=True)

    if image.status_code == 200:
        with open(path, "wb") as f:
            try:
                f.write(image.content)
            finally:
                f.close()

    changeWallpaper(path);


def loadConfigs(dir):
    global chosenSource
    global sources
    userDefinedSources = []
    configs = ""
    with open(dir + "/config.json", "r") as f:
        try:
            configs = f.read()
        finally:
            f.close()

    configs = json.loads(configs)
    chosenSource = configs["source"]
    userDefinedSources = configs["userDefinedSources"]
    sources.extend(userDefinedSources)

def isFirstLaunch(dir): #checks if its the first time script is launched
    if not os.path.isdir(dir) or not os.path.isfile(dir+'/config.json') or not os.path.isfile(dir+'/pidgeon.py'):
        return True
    else:
        return False

def install(dir):
    #TODO if something fails, run uninstall
    # TODO ask for source on install
    configFilePath = dir + "/config.json"
    defaultConfig = {
    "source": "bing",
    "userDefinedSources": []
    }
    jsonString = json.dumps(defaultConfig)

    #make directory
    if not os.path.isdir(dir):
        print(f'[{chr(10004)}] Making directory {dir}')
        os.mkdir(dir)

    #write default config
    with open(configFilePath, "w") as f:
        try:
            print(f'[{chr(10004)}] Writing default configuration file to {configFilePath}')
            f.write(jsonString)
        finally:
            f.close()
    if not os.path.isfile(dir + '/pidgeon.py'):
        #copy script to dir
        print(f'[{chr(10004)}] Copying script to {dir}/pidgeon.py')
        os.system(f'cp ./pidgeon.py {dir}')

    print(f'[{chr(10004)}] Installing cronjob on reboot...')
    addPidgeonCronjob(dir)
    print('Installation done')

def chooseSource(dir):
    f = open(dir + '/config.json', 'r+')
    config = f.read()
    config = json.loads(config)
    isValidInput = False


    print(f'Current chosen source: {chosenSource}')
    print('Available sources:\n')
    for index, source in enumerate(sources):
        print(f'{index+1}) {source["name"]}')

    while not isValidInput:
        newSource = input()
        if not newSource.isdigit():
            isValidInput = False
        else:
            newSource = int(newSource) - 1
            if newSource < 0 or newSource > len(sources)-1:
                print('out of bounds')
                isValidInput = False
            else:
                isValidInput = True

    config['source'] = sources[newSource]['configName']
    f.seek(0)
    f.write(json.dumps(config))
    f.truncate()
    f.close()

    print(f'[{chr(10004)}] Source changed to {sources[newSource]["name"]}')

    print('\nDo you want to fetch image from new source? Y/n')
    fetchNewImage = yesNoPrompt()
    if fetchNewImage:
        print(f'Fetching from {sources[newSource]["name"]}...')
        return
    else:
        exit(0)

def changeWallpaper(path):
    desktopEnvironment = os.environ.get('XDG_CURRENT_DESKTOP')
    commands = {
        'GNOME': 'gsettings set org.gnome.desktop.background picture-uri "file://{}"',
        'KDE':  """
                qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
                    var allDesktops = desktops();
                    print (allDesktops);
                    for (i=0;i<allDesktops.length;i++) {{
                        d = allDesktops[i];
                        d.wallpaperPlugin = "org.kde.image";
                        d.currentConfigGroup = Array("Wallpaper",
                                               "org.kde.image",
                                               "General");
                        d.writeConfig("Image", "file:///{}")
                    }}
                '
            """,
        'MATE': 'gsettings set org.mate.background picture-filename {}',
        'I3': '"feh --bg-scale {}'
    }

    if desktopEnvironment in commands:
        commandForDE = commands[desktopEnvironment].format(path)
    else:
        print('Your desktop environment is not supported yet.')
        print(f"You can try setting your wallpaper to the image in {path} from your desktop environment's settings")
        exit(1)

    os.system(commandForDE)

def addPidgeonCronjob(dir):
    currentCrontab  = ''
    crontabOutput = subprocess.run(['crontab', '-l'], capture_output = True)
    if(crontabOutput.returncode == 0):
        currentCrontab = str(crontabOutput.stdout)[2:-1]

    currentCrontab = removePidgeonCronjob(currentCrontab, dir)
    newCrontab = currentCrontab + f'\n@reboot python {dir}/pidgeon.py\n'
    newCrontab = newCrontab.encode()

    cronOut = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
    cronOut.stdin.write(newCrontab)

def removePidgeonCronjob(currentCrontab, dir):
    return currentCrontab.replace(f'@reboot python3 {dir}/pidgeon.py', '')

def getCorrespondingUrl():
    for source in sources:
        if chosenSource == source['configName']:
            if source['url']:
                return source['url']
            else:
                return source['urlFunc']()
    print('Source not defined')
    exit(1)

def yesNoPrompt():
    while True:
        choice = input()
        if choice == '' or choice.upper()[0] == 'Y':
            return True
        elif choice.upper()[0] == 'N':
            return False

def parseArgs():
    # TODO add uninstall -u flag
    # TODO add reinstall -r flag
	parser = argparse.ArgumentParser(description='Fetch a brand new wallpaper everyday')
	parser.add_argument('-c','--config', action='store_true', help='Configuration, add sources, how ofter to change.')
	args = parser.parse_args()
	return args

if __name__ == "__main__":
    main()
