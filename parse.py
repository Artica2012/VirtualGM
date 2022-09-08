import importer
import exporter

def parser(database):
    exporter.export_to_sql(importer.importDisease('ddiDisease.txt'))
    exporter.export_to_sql(importer.importFeat('ddiFeat.txt'))
    exporter.export_to_sql(importer.importItem('ddiItem.txt'))
    exporter.export_to_sql(importer.importPower('ddiPower.txt'))
    return()
