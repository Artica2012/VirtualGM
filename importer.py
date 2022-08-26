# import data

def importDisease(filename):
    with open(f'data/{filename}', 'r', encoding='utf-8') as file:
        data_cache = []
        for line in file.readlines():
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(prefix)
            # print(linedata[1])
            data = linedata[1].split(',')
            ID = data[0].removeprefix('(').strip("'")
            #print(editedtext)
            # print(data)
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Name': data[1],
                'Level': data[2],
                'Source': data[3],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            #print(data_dict)
            data_cache.append(data_dict)
    index = ['Type', 'ID', 'Name', 'Level', 'Source', 'URL']
    return (data_cache, index, prefix)

def importFeat(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            #print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            #print(prefix)
            #print(linedata[1])
            data = linedata[1].split(',')
            ID = data[0].removeprefix('(').strip("'")
            #print(editedtext)
            # print(data)
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Name': data[1],
                'Tier': data[5],
                'Source': data[4],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            #print(data_dict)
            data_cache.append(data_dict)
    index = ['Type', 'ID', 'Name', 'Tier', 'Source', 'URL']
    return (data_cache, index, prefix)

def importItem(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            #print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            #print(prefix)
            #print(linedata[1])
            data = linedata[1].split(',')
            ID = data[0].removeprefix('(').strip("'")
            #print(editedtext)
            #print(data)
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Name': data[1],
                'Cost': data[2],
                'Level': data[4],
                'Category': data[5],
                'Source': data[8],
               # 'Text': editedtext,
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            #print(data_dict)
            data_cache.append(data_dict)
            index = ['Type', 'ID', 'Name', 'Cost', 'Level', 'Category', 'Source', 'URL']
    return (data_cache, index, prefix)

def importPower(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            #print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            #print(prefix)
            #print(linedata[1])
            data = linedata[1].split(',')
            ID = data[0].removeprefix('(').strip("'")
            #print(editedtext)
            #print(data)
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Name': data[1],
                'Level': data[2],
                'Action': data[3],
                'Class': data[7],
                'Source': data[6],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            #print(data_dict)
            data_cache.append(data_dict)

    index = ['Type', 'ID', 'Name', 'Level', 'Action', 'Class', "Source", 'URL']

    return (data_cache, index, prefix)
