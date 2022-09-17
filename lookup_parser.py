# lookup_parser.py
import importer
import exporter

def parser():
    exporter.disease_export(importer.import_disease('ddiDisease.txt'))
    exporter.feat_export(importer.import_feat('ddiFeat.txt'))
    # exporter.export_to_sql(importer.importItem('ddiItem.txt'))
    exporter.power_export(importer.import_power('ddiPower.txt'))
    return()
