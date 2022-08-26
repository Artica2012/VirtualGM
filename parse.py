import importer
import exporter

def parser(database):
    exporter.export_to_sql(importer.importDisease('ddiDisease.txt'), database)
    exporter.export_to_sql(importer.importFeat('ddiFeat.txt'), database)
    exporter.export_to_sql(importer.importItem('ddiItem.txt'), database)
    exporter.export_to_sql(importer.importPower('ddiPower.txt'), database)
    return()
