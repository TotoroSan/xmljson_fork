from json import dumps

import xmljson
import lxml.etree as ET




def my_test():
    # only works with LXML-Tree
    parser = ET.XMLParser()
    tree = ET.parse("C:/Users/Gsell/PycharmProjects/xmljson/tests/GSE169013_family.xml", parser)
    root = tree.getroot()


    #Fixme gucken wie ich dass in code einbaue -> wenn ich das in code ziehe, ist es im MINiML Element, da im letzteten
    # schritt das ganze element unter die wurzel gehängt wird
    # get docinfo
    xml_version = tree.docinfo.xml_version
    encoding = tree.docinfo.encoding
    standalone_flag = tree.docinfo.standalone

    json_object = {}
    json_object.update({"xml_prolog": {"xml_version": xml_version, "encoding": encoding, "standalone": standalone_flag}})


    # False = namespaces only in "header", True = namespaces for every object
    badgerfish_converter = xmljson.BadgerFish(ns_as_attrib=False, ns_prefix=True, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    gdata_converter = xmljson.GData(ns_as_attrib=False, ns_prefix=True, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    abdera_converter = xmljson.Abdera(ns_as_attrib=True, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    parker_converter = xmljson.Parker(xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    cobra_converter = xmljson.Cobra()
    json_object.update(abdera_converter.data(root))

    print(dumps(json_object))





my_test()
