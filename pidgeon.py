#!/usr/bin/env python3
import requests
import os
from pathlib import Path
import json
import argparse
import subprocess
import re
from datetime import date, timedelta
import getpass

def getBingUrl():
    try:
        res = requests.get("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US")
    except:
            os.system('notify-send "Could not retrieve wallpaper" "pidgeon.py"')

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
            os.system('notify-send "Could not retrieve wallpaper" "pidgeon.py"')
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

def getNatgeoUrl():
    currentDate = date.today()
    month = str(currentDate.month)
    year = str(currentDate.year)
    month = month if len(month) != 1 else '0' + month

    try:
        monthGallery = requests.get(f'https://www.nationalgeographic.com/photography/photo-of-the-day/_jcr_content/.gallery.{year}-{month}.json').json()
    except:
        os.system('notify-send "Could not retrieve wallpaper" "pidgeon.py"')
        exit(1)
    latestImageUrl = monthGallery['items'][0]['image']['uri']
    return latestImageUrl

# Global Variables
chosenSource = ''
desktopEnvironment = ''
dir = '/opt/pidgeon.py'
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
    },
    {
        'name': 'National Geographic Photo of the Day',
        'urlFunc': getNatgeoUrl,
        'configName': 'natgeo',
        'url': ''
    }
]

def main():
    args = parseArgs()
    path = dir + "/wallpaper.jpg"

    if isFirstLaunch():
        print("First time running, do you want to install? Y/n")
        wantsToInstall = yesNoPrompt()
        if wantsToInstall:
            if os.geteuid() == 0:
                print('Run as normal user, without sudo')
                exit(1)
            install()
        else:
            exit(0)

    loadConfigs()

    if args.config:
        chooseSource()
        loadConfigs()
    elif args.uninstall:
        if os.geteuid() != 0:
            print('Run as root, sudo pidgeon.py -u')
            exit(1)
        uninstall()
        exit(0)

    url = getCorrespondingUrl()
    image = requests.get(url, stream=True)

    if image.status_code == 200:
        with open(path, "wb") as f:
            try:
                f.write(image.content)
            finally:
                f.close()

    changeWallpaper(path)

def loadConfigs():
    global chosenSource
    global sources
    global desktopEnvironment
    global dir

    userDefinedSources = []
    configs = ""
    with open(dir + "/config.json", "r") as f:
        try:
            configs = f.read()
        finally:
            f.close()

    configs = json.loads(configs)
    chosenSource = configs['source']
    desktopEnvironment = configs['desktopEnvironment']
    userDefinedSources = configs["userDefinedSources"]
    sources.extend(userDefinedSources)

def isFirstLaunch(): #checks if its the first time script is launched
    if not os.path.isdir(dir) or not os.path.isfile(dir+'/config.json') or not os.path.isfile(dir+'/pidgeon.py'):
        return True
    else:
        return False

def install():
    configFilePath = dir + "/config.json"
    defaultConfig = {
    "source": "bing",
    "userDefinedSources": [],
    "desktopEnvironment": os.environ.get('XDG_CURRENT_DESKTOP')
    }
    jsonString = json.dumps(defaultConfig)

    #make directory
    if not os.path.isdir(dir):
        print(f'[{chr(10004)}] Making directory {dir}')
        currentUser = getpass.getuser()
        try:
            os.system(f'sudo mkdir {dir}')
            os.system(f'sudo chown {currentUser} {dir}')
        except:
            print(f'Could not create directory at {dir}')
            uninstall()
            exit(1)

    #write default config
    with open(configFilePath, "w") as f:
        try:
            print(f'[{chr(10004)}] Writing default configuration file to {configFilePath}')
            f.write(jsonString)
        except:
            print(f'Could not write configuration file to {configFilePath}')
            uninstall()
            exit(1)
        finally:
            f.close()

    #copy the pidgeon.py script to the ~/wallpaper directory
    if not os.path.isfile(dir + '/pidgeon.py'):
        #copy script to dir
        print(f'[{chr(10004)}] Copying script to {dir}/pidgeon.py')
        try:
            os.system(f'cp ./pidgeon.py {dir}')
            os.system(f'sudo chmod +x {dir}/pidgeon.py')
            os.system(f'sudo ln -s {dir}/pidgeon.py /bin')
        except:
            print(f'Could not copy script pidgeon.py to {dir}')
            uninstall()
            exit(1)

    #write anacron interface script
    print(f'[{chr(10004)}] Creating anacron interface script in {dir}/anacron-interface.py')
    try:
        createAnacronInterfaceScript()
    except:
        print(f'Could not write anacron interface script to {dir}')
        uninstall()
        exit(1)

    #Create cronjob
    print(f'[{chr(10004)}] Creating anacron entry...')
    try:
        os.system(f'sudo python3 {dir}/anacron-interface.py')
    except:
        print('Could not install pidgeon.py cronjob to anacrontab')
        uninstall()
        exit(1)

    print('Installation done\n\n')

    #ask for source and write to config
    chooseSource()

def uninstall():
    # Remove pidgeon.py from anacrontab
    print(f'[{chr(10004)}] Removing pidgeon.py from anacrontab')
    try:
        os.system(f'sudo python3 {dir}/anacron-interface.py -r')
    except:
        print('Failed to remove pidgeon.py from /etc/anacrontab')
        exit(1)

    print(f'[{chr(10004)}] Removing symlink to {dir}/pidgeon.py in /bin')
    try:
        os.system(f'sudo rm /bin/pidgeon.py')
    except:
        print(f'Failed to remove symlink to {dir}/pidgeon.py in /bin')
        exit(1)
    print(f'[{chr(10004)}] Removing {dir}/')
    try:
        os.system(f'sudo rm -r {dir}')
    except:
        print(f'Failed to remove {dir}/')
        exit(1)

    print('Uninstalled Succesfully')

def chooseSource():
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
    else:
        exit(0)

def changeWallpaper(path):
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

    try:
        os.system(commandForDE)
    except:
        os.system('notify-send "Could not set wallpaper" "pidgeon.py"')

def createAnacronInterfaceScript():
    script = """
import argparse
def parseArgs():
    parser = argparse.ArgumentParser(description='Add or remove pidgeon.py cronjob from anacrontab')
    parser.add_argument('-r','--remove', action='store_true', help='Remove pidgeon.py cronjob from anacrontab')
    args = parser.parse_args()
    return args
def addPidgeonCronjob():
    removePidgeonCronjob()
    with open('/etc/anacrontab', 'r+') as f:
        currentCrontab = f.read()
        newCrontab = f'{currentCrontab}@daily 0 pidgeon.py pidgeon.py\\n'
        f.seek(0)
        f.write(newCrontab)
        f.truncate()
        f.close()
def removePidgeonCronjob():
    with open('/etc/anacrontab', 'r+') as f:
        currentCrontab = f.read()
        newCrontab = currentCrontab.replace(f'@daily 0 pidgeon.py pidgeon.py\\n', '')
        f.seek(0)
        f.write(newCrontab)
        f.truncate()
        f.close()
args = parseArgs()
if args.remove:
    removePidgeonCronjob()
else:
    addPidgeonCronjob()
    """
    with open(f'{dir}/anacron-interface.py', 'w+') as f:
        f.write(script)
        f.close()

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
	parser = argparse.ArgumentParser(description='Fetch a brand new wallpaper everyday')
	parser.add_argument('-c','--config', action='store_true', help='Configuration, add sources, how ofter to change.')
	parser.add_argument('-u','--uninstall', action='store_true', help='Uninstall pidgeon and delete all files')
	args = parser.parse_args()
	return args

if __name__ == "__main__":
    main()
