# importer.py

# imports
from bs4 import BeautifulSoup


# import the disease database
def import_disease(filename):
    with open(f'data/{filename}', 'r', encoding='utf-8') as file:  # open the file
        data_cache = []
        for line in file.readlines():
            # Strip the extra headers off of each line and split it up
            # NOT PERFECT
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(prefix)
            # print(linedata[1])
            data = linedata[1].split(',', 5)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(data)

            # attempt at using beautiful soup to get data from the last cell
            # soup = BeautifulSoup(data[5], "html.parser")
            # text = soup.get_text()
            # text = text.strip(r'\r')
            # text = text.strip(r'\n')
            # print(text)

            # Export the data from the line into a dictionary
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1],
                'Level': data[2].strip("'"),
                'Source': data[3],
                'Data': data[5],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }

            # print(data[5])
            data_cache.append(data_dict)  # add that dict to the list of dicts
    return data_cache  # return a tuple with the data, the index and the database title to be read by
    # the exporter


def import_feat(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(prefix)
            # print(linedata[1])
            data = linedata[1].split(',', 7)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(data[7])
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1].strip("'"),
                'Tier': data[5].strip("'"),
                'Source': data[4],
                'Data': data[7],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            # print(data_dict)
            data_cache.append(data_dict)

    return data_cache


# TODO - Fix the item URL. Need to manually check URLs to figure out who it builds it.
def import_item(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(prefix)
            # print(linedata[1])
            data = linedata[1].split(',', 9)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(data)
            if data[4].strip("'") == "Armor":
                prefix = "Armor"
            elif data[4].strip("'") == 'Implement':
                prefix = "Implement"
            elif data[4].strip("'") == 'Weapon':
                prefix = 'Weapon'
            else:
                prefix = 'Item'


            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1].strip("'"),
                'Category': data[5],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            data_cache.append(data_dict)
    return data_cache


def import_power(filename):
    with open(f'data/{filename}', 'r', encoding='utf8') as file:
        data_cache = []
        for line in file.readlines():
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(prefix)
            # print(linedata[1])
            data = linedata[1].split(',', 9)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(data)
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1].strip("'"),
                'Level': data[2].strip("'"),
                'Action': data[3].strip("'"),
                'Class': data[7],
                'Source': data[6],
                'Data': data[9],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            # print(data[9])
            data_cache.append(data_dict)

    return data_cache

# import the monster database
def import_monster(filename):
    with open(f'data/{filename}', 'r', encoding='utf-8') as file:  # open the file
        data_cache = []
        for line in file.readlines():
            # Strip the extra headers off of each line and split it up
            # NOT PERFECT
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(f'prefix: {prefix}')
            # print(f'linedata[1]: {linedata[1]}')
            data = linedata[1].split(',', 8)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(f"data: {data}")

            # attempt at using beautiful soup to get data from the last cell
            # soup = BeautifulSoup(data[5], "html.parser")
            # text = soup.get_text()
            # text = text.strip(r'\r')
            # text = text.strip(r'\n')
            # print(text)

            # Export the data from the line into a dictionary
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1],
                'Data': data[5],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }

            # print(data[5])
            data_cache.append(data_dict)  # add that dict to the list of dicts
    return data_cache  # return a tuple with the data, the index and the database title to be read by
    # the exporter

# import the monster database
def import_Ritual(filename):
    with open(f'data/{filename}', 'r', encoding='utf-8') as file:  # open the file
        data_cache = []
        for line in file.readlines():
            # Strip the extra headers off of each line and split it up
            # NOT PERFECT
            # print(line)
            line = line.removeprefix('INSERT INTO ')
            linedata = line.split('VALUES ')
            prefix = linedata[0].split()[0].strip("`")
            # print(f'prefix: {prefix}')
            # print(f'linedata[1]: {linedata[1]}')
            data = linedata[1].split(',', 8)
            ID = data[0].removeprefix('(').strip("'")
            # print(editedtext)
            # print(f"data: {data}")

            # attempt at using beautiful soup to get data from the last cell
            # soup = BeautifulSoup(data[5], "html.parser")
            # text = soup.get_text()
            # text = text.strip(r'\r')
            # text = text.strip(r'\n')
            # print(text)

            # Export the data from the line into a dictionary
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }

            # print(data[5])
            data_cache.append(data_dict)  # add that dict to the list of dicts
    return data_cache  # return a tuple with the data, the index and the database title to be read by
    # the exporter