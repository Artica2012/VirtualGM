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
            data_dict = {
                'Type': prefix,
                'ID': data[0].removeprefix('(').strip("'"),
                'Title': data[1].strip("'"),
                'Cost': data[2],
                'Level': data[4],
                'Category': data[5],
                'Source': data[8],
                'Text': data[9],
                'URL': f"http://iws.mx/dnd/?view={prefix.lower()}{ID}"
            }
            # print(data[9])
            data_cache.append(data_dict)
            index = ['Type', 'ID', 'Title', 'Cost', 'Level', 'Category', 'Source', 'URL']
    return data_cache, index, prefix


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
