from json import dumps

from xmlschema import XsdGlobals

import xmljson
import lxml.etree as ET

# testing this
import xmlschema
from pprint import pprint

def my_test():
    # only works with LXML-Tree
    tree = ET.parse("C:/Users/Gsell/PycharmProjects/xmljson/tests/GSE169013_family.xml")
    root = tree.getroot()

    #schema_tree = ET.parse("C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    #schema_root = schema_tree.getroot()



    # ------------------------  XMLSCHEMA -----------------------------------
    my_schema = xmlschema.XMLSchema("C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")






    #badgerfish_converter = xmlschema.BadgerFishConverter(strip_namespaces=False)

    # for child in root:
    #     print(child.nsmap)

    # TODO so kriege ich alle schema komponenten
    #for xsd_component in my_schema.types.values():
    #    print (xsd_component)
    namespaces = {'':"http://www.ncbi.nlm.nih.gov/geo/info/MINiML"}
    # schema_element = my_schema.find('//{http://www.ncbi.nlm.nih.gov/geo/info/MINiML}Contributor')
    # schema_types = schema_element.type
    # #extract simple type from complex type:
    # schema_simple_type = schema_types.simple_type
    #
    # print(schema_types)

    #print(schema_types.is_complex())
    #print (schema_types.has_complex_content())



    #type.is_simple() to check if type is simple

    #base_type = my_schema.find('//'+'Contributor')
    #print(base_type)


    # print(schema_types)
    # schema_attribut = schema_types.attributes
    # print(schema_attribut)
    # #print(schema_attribut)
    #
    # print(schema_attribut.get("database").type)
    #for attrib in schema_attribut.iter_components():
        #if attrib.name != None:
            #print (attrib.name)
            #print (attrib.type)


    # TODO vorlage für alternative implementierung
    #stack = []
    #xsd_element = my_schema.elements["Contributor"]
    #stack.append(xsd_element)

    # stack muss globaler natur sein
    #for i in xsd_element:
    #    if i.tag == "{http://www.ncbi.nlm.nih.gov/geo/info/MINiML}Person":
    #        stack.append(i)



    # # TODO get all types from contributor key
    # # this gives the element contributor
    #testing = my_schema.elements['MINiML']
    #for item in testing:
        #print(item.local_name)


    #
    # # this gives the content of the type description of the element
    # testing_type = testing.type.content
    #
    # # FIXME this is important
    # # this gives the attributes of the type
    #testing_attribute = testing.type.attributes
    #for item in testing_attribute.iter_components():
    #
    #     # get names of attributes (all non attributes are none)
    # if item.name != None:
    #         print (item.name)
    #         # this i can use to check type
    #         print (item.type)

    #print(testing_type)
    # this iterates over content of the complex type definition
    #for item in testing_type.iter_components():
    #    print(item)

    #print(testing_type)
    #print(my_schema.elements.keys())

    #for key in my_schema.elements.keys():
        #print (key)

    #print(testing_type)
    #print(my_schema.to_dict("C:/Users/Gsell/PycharmProjects/xmljson/tests/GSE169013_family.xml"))
    #print(my_schema.is_valid(tree))

    # this can also be used to transform the data
    # process_namespaces to incorporate namespaces on top level or as prefix => False = prefixed, True = toplevel
    # TODO check if there is option for namespaces as attributes
    # validation strict = fails if not valid, lax = runs but gathers errors in json, skip = ignore schema validation
    #mydict = (my_schema.to_dict(tree, validation="skip", converter = badgerfish_converter, process_namespaces = True))


    #print(xmlschema.to_json(tree, converter=badgerfish_converter, process_namespaces=False))











    # fixme überlegen, dass direkt in abdera, parker, yahoo dode einzubauen
    # use this for abdera, parker, yahoo to remove namespace qualifications from elementtags

    # TODO remove prefix from xsi schema location
    #for elem in root.getiterator():
    #     elem.tag = ET.QName(elem).localname


    #print(ET.tostring(root, pretty_print=True))
    # False = namespaces only in "header", True = namespaces for every object
    badgerfish_converter = xmljson.BadgerFish(ns_as_attrib=True, xml_schema="C:/Users/Gsell/PycharmProjects/xmljson/tests/MINiML.xsd")
    json_object = (badgerfish_converter.data(root))
    print(dumps(json_object))
    #if root.text:
     #   print("salam")

    #print(xmljson.gdata.data(root))

    #Fixme gucken wie ich dass in code einbaue
    # get docinfo
    #xml_version = tree.docinfo.xml_version
    #encoding = tree.docinfo.encoding
    #standalone_flag = tree.docinfo.standalone

    # maybe put doc information in "docinfo" object, to quickly access all necessary info
    # set docinfo
    #json_object["version"] = xml_version
    #json_object["encoding"] = encoding
    #json_object["standalone"] = standalone_flag



    # FIXME über CLI ist doc-header noch nicht enthalten // Header Info ggf. in Objekt mit Key "Header" packen.



    #fixme rücktransformation funzt noch nicht -> checken // invalid tag name
    #

    #print(dumps(xmljson.abdera.data(ET.fromstring('<reports><entry id="fuffiz"><id>Igel</id></entry><entry><id>Hase</id></entry></reports>'))))

my_test()
