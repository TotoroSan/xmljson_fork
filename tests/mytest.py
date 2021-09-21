from json import dumps

import xmljson
import lxml.etree as ET




def my_test():
    # only works with LXML-Tree
    # removing blank text is important, otherwise the transformation will not work, since line breaks are counted as text.
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse("C:/Users/Gsell/PycharmProjects/xmljson_fork/tests/GSE99572_family.xml", parser)
    root = tree.getroot()


    #Fixme gucken wie ich dass in code einbaue -> wenn ich das in code ziehe, ist es im MINiML Element, da im letzteten
    # schritt das ganze element unter die wurzel gehängt wird
    # get docinfo
    xml_version = tree.docinfo.xml_version
    encoding = tree.docinfo.encoding
    standalone_flag = tree.docinfo.standalone

    json_object = {}
    json_object.update({"xml_prolog": {"xml_version": xml_version, "encoding": encoding, "standalone": standalone_flag}})


    # ns_as_attrib: False => namespaces only in "header", True => namespaces for every object

    #, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    badgerfish_converter = xmljson.BadgerFish(ns_as_attrib=True, ns_as_prefix=False, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd") #ns_as_attrib=False, ns_as_prefix=True)
    gdata_converter = xmljson.GData(ns_as_attrib=True, ns_as_prefix=False)
    abdera_converter = xmljson.Abdera(xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")#ns_as_attrib=True, )
    #parker_converter = xmljson.Parker(ns_as_prefix=True)#xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    #cobra_converter = xmljson.Cobra()
    json_object.update(abdera_converter.data(root))

    print(dumps(json_object))

    xml_string = '<alice xmlns="http://some-namespace" xmlns:charlie="http://some-other-namespace">' \
                     '<charlie:joe>bob</charlie:joe><david>richard</david></alice>'
    #xml_string2= '<root><x/><y><z/></y></root>'

    #tree2 = ET.parse("C:/Users/Gsell/PycharmProjects/xmljson_fork/tests/abdera-1.xml")
    #second = abdera_converter.data(tree2.getroot())
    #print(dumps(json_object))

    #xml_obj = gdata_converter.etree(json_object)
    # transform to xml string
    #for elem in xml_obj:
        #print(ET.tostring(elem)) # das ist root element das die anderen elemnte enthält, hat aber nicht die root funktionen aus irgend einem grund

    #print(ET.tostring(xml_obj[0]))

    #second = gdata_converter.data(ET.fromstring(xml_string))
    #print(dumps(second))


        #elem.tag = ET.QName(elem).localname


    #print(badgerfish_converter.etree(json_object))


my_test()
