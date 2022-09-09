import importer
import exporter

def parser():
    exporter.disease_export(importer.importDisease('ddiDisease.txt'))
    exporter.feat_export(importer.importFeat('ddiFeat.txt'))
    # exporter.export_to_sql(importer.importItem('ddiItem.txt'))
    exporter.power_export(importer.importPower('ddiPower.txt'))
    return()
