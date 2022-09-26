# lookup_parser.py
import importer
import exporter


def parser():
    exporter.disease_export(importer.import_disease('ddiDisease.txt'))
    exporter.feat_export(importer.import_feat('ddiFeat.txt'))
    exporter.item_export(importer.import_item('ddiItem.txt'))
    exporter.power_export(importer.import_power('ddiPower.txt'))
    exporter.monster_export(importer.import_monster('ddiMonster.txt'))
    exporter.ritual_export(importer.import_Ritual('ddiRitual.txt'))
    return ()
