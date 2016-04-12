import json
import os
import aiohttp

current_dir = os.path.dirname(os.path.realpath(__file__)) # Current path where Read.py is
main_dr = os.path.sep.join(current_dir.split(os.path.sep)[:-2]) #Current Path where Working bot is


#Command and role which is custom command.
with open(current_dir+"/Bot_Config.json") as f:
    Bot_Config = json.load(f)

#Config setting with ID, link,account etc
with open(main_dr+"/Config.json") as f:
    config = json.load(f)

website=config["link"]

if os.path.isfile("Cogs/Utils/New_Bot_Config.json"):
    print ("Detected update files\nUpdating..")
    with open(os.path.join("Cogs/Utils","New_Bot_Config.json"),"r") as f:
        Temp = json.load(f)
        New = dict(Temp)
        Old = dict(Bot_Config)
        for main in Old:
            if type(Old[main]) is not dict:
                continue
            else:
                for sub in Old[main]:
                    New[main][sub].update(Old[main][sub])

        with open (os.path.join("Cogs/Utils","Bot_Config.json"),'w') as f:
            json.dump(New,f,sort_keys=True,indent=2)
    # print(json.dumps(Temp,sort_keys=True,indent=4))
    os.remove("Cogs/Utils/New_Bot_Config.json")
    print("Update!")


async def ReadFiles(folder,files):  # Read and get info from the files inside a folder
    with open(os.path.join(folder,files), 'r') as f:
        data = json.load(f)
    print(files, " Read")
    return (data)

async def InputFiles(data,folder,files):  # Input data info into files Inside a folder
    with open(os.path.join(folder,files), 'w') as f:
        json.dump(data, f,sort_keys=True, indent=2)
    print(files, " Updated")
