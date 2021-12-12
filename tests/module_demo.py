from json import dumps
import xmljson
import lxml.etree as ET
from pprint import pprint

def my_demo():
    """Demo script for XML-to-JSON-Conversion"""

    test_file = "GSE179926_family.xml"

    # minimize xml file
    f = open(test_file, "r")
    string_without_line_breaks = ""
    for line in f:
        stripped_line = line.rstrip()
        string_without_line_breaks += stripped_line
    f.close()
    f = open(test_file, "w")
    f.write(string_without_line_breaks)
    f.close()

    # removing blank text is important, since line breaks are counted as text.
    parser = ET.XMLParser(remove_blank_text=True)  # create lxml parser
    tree = ET.parse(test_file, parser)  # parse test_file with the parser to lxml tree
    root = tree.getroot()  # get root element of the tree - used as parameter in data(root) method

    # get xml-prolog info - is done here since tree meta information is not passed to converter
    xml_version = tree.docinfo.xml_version
    encoding = tree.docinfo.encoding
    standalone_flag = tree.docinfo.standalone

    # add prolog info (if needed)
    json_object = {}
    json_object.update({"xml_prolog": {"xml_version": xml_version, "encoding": encoding, "standalone": standalone_flag}})


    # ns_as_attrib: False => namespaces only in root element, True => namespaces in every object

    xml_schema="MINiML.xsd"


    # create converter objects, effect of parameters is commented in __init__.py constructor
    badgerfish_converter = xmljson.BadgerFish()
    abdera_converter = xmljson.Abdera()
    parker_converter = xmljson.Parker()
    gdata_converter = xmljson.GData(harmonize_synonyms=True, ns_as_attrib=True, ns_as_prefix=False, xml_schema=xml_schema)
    # this returns the json dictionary for the input data
    json_dict = gdata_converter.data(root)

    # this updates the existing dict that already contains prolog information
    json_object.update(json_dict)

    # print the result - if prolog is not needed we can directly insert json_dict and not json_object
    print(dumps(json_object))

    # use ET.fromstring if you need to parse from a xml_string directly rather than an input file
    #json_dict_fromstring = gdata_converter.data(ET.fromstring(xml_string))



my_demo()
