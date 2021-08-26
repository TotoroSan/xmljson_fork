# -*- coding: utf-8 -*-

import sys
from collections import Counter, OrderedDict
from io import BytesIO
import xmlschema

import lxml.etree as ET
from xmlschema.validators import XsdAtomicBuiltin

try:
    from lxml.etree import Element, iterparse, ElementTree
except ImportError:
    from xml.etree.cElementTree import Element

__author__ = 'S Anand'
__email__ = 'root.node@gmail.com'
__version__ = '0.2.0'

# Python 3: define unicode() as str()
if sys.version_info[0] == 3:
    unicode = str
    basestring = str



class XMLData(object):
    def __init__(self, xml_fromstring=True, xml_tostring=True, element=None, dict_type=None,
                 list_type=None, attr_prefix=None, text_content=None, simple_text=False, ns_name=None, ns_as_attrib=True,
                 invalid_tags=None, xml_schema=None):
        # xml_fromstring == False(y) => '1' -> '1'
        # xml_fromstring == True     => '1' -> 1
        # xml_fromstring == fn       => '1' -> fn(1)
        if callable(xml_fromstring):
            self._fromstring = xml_fromstring
        elif not xml_fromstring:
            self._fromstring = lambda v: v
        # custom conversion function to convert data string to XML string
        if callable(xml_tostring):
            self._tostring = xml_tostring
        # custom etree.Element to use
        self.element = Element if element is None else element
        # dict constructor (e.g. OrderedDict, defaultdict)
        self.dict = OrderedDict if dict_type is None else dict_type
        # list constructor (e.g. UserList)
        self.list = list if list_type is None else list_type
        # Prefix attributes with a string (e.g. '$')
        self.attr_prefix = attr_prefix
        # Key that stores text content (e.g. '$t')
        self.text_content = text_content
        # simple_text == False or None or 0 => '<x>a</x>' = {'x': {'a': {}}}
        # simple_text == True               => '<x>a</x>' = {'x': 'a'}
        self.simple_text = simple_text

        # Namespace Marking
        self.ns_name = ns_name
        self.is_doc_root = True  # initial document root
        self.ns_as_attrib = ns_as_attrib

        # store the current root of (partial) schema tree
        self.root_schema_element = None
        # store the current schema element
        self.schema_element = None

        self.lxml_lib = True

        self.schema_stack = []
        self.schema_attribute_stack = []


        # if we use schema to type / only works for Abdera, Badgerfish, Gdata and Parker
        if xml_schema is None:
            self.schema_typing = False
        else:
            # pass XML schema location as string, create XMLSchema Object with it
            self.xml_schema = xmlschema.XMLSchema(xml_schema)
            self.schema_typing = True




        # invalid_tags == 'drop' => tags like $ are ignored
        if invalid_tags == 'drop':
            self._element = self.element
            self.element = self._make_valid_element
        elif invalid_tags is not None:
            raise TypeError('invalid_tags can be "drop" or None, not "%s"' % invalid_tags)

    def _make_valid_element(self, key):
        try:
            return self._element(key)
        except (TypeError, ValueError):
            pass

    @staticmethod
    def _tostring(value):
        '''Convert value to XML compatible string'''
        if value is True:
            value = 'true'
        elif value is False:
            value = 'false'
        else:
            value = str(value)
        return unicode(value)       # noqa: convert to whatever native unicode repr

    def _typemapping(self, content, xsd_type):
        '''Convert content to json types according to mapping of xsd_simpletype'''

        convert_to_string = ["XsdAtomicBuiltin(name='xs:ID')", "XsdAtomicBuiltin(name='xs:string')",
                             "XsdAtomicBuiltin(name='xs:normalizedString')",
                             "XsdAtomicBuiltin(name='xs:date')", "XsdAtomicBuiltin(name='xs:time')",
                             "XsdAtomicBuiltin(name='xs:anyURI')", "XsdAtomicBuiltin(name='xs:token')",
                             "XsdAtomicBuiltin(name='xs:IDREF')","XsdAtomicBuiltin(name='xs:NCName')"]
        convert_to_int = ["XsdAtomicBuiltin(name='xs:positiveInteger')", "XsdAtomicBuiltin(name='xs:nonNegativeInteger')",
                          "XsdAtomicBuiltin(name='xs:integer')"]
        convert_to_bool = ["XsdAtomicBuiltin(name='xs:boolean')"]

        if str(xsd_type) is None:
            return str(content)
        if str(xsd_type) in convert_to_string:
            return str(content)
        if str(xsd_type) in convert_to_int:
            return int(content)
        if str(xsd_type) in convert_to_bool:
            return bool(content)


    @staticmethod
    def _fromstring(value):
        '''Convert XML string value to None, boolean, int or float'''

        # NOTE: Is this even possible ?
        if value is None:
            return None

        # FIXME: In XML, booleans are either 0/false or 1/true (lower-case !)
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False

        # FIXME: Using int() or float() is eating whitespaces unintendedly here
        try:
            if value.lower().startswith('0'):
                return value.lower()
            else:
                return int(value.lower())
        except ValueError:
            pass

        try:
            # Test for infinity and NaN values
            if float('-inf') < float(value) < float('inf'):
                return float(value)
        except ValueError:
            pass

        return value

    def etree(self, data, root=None):
        '''Convert data structure into a list of etree.Element'''
        result = self.list() if root is None else root
        if isinstance(data, (self.dict, dict)):
            for key, value in data.items():
                value_is_list = isinstance(value, (self.list, list))
                value_is_dict = isinstance(value, (self.dict, dict))
                # Add attributes and text to result (if root)
                if root is not None:
                    # Handle attribute prefixes (BadgerFish)
                    if self.attr_prefix is not None:
                        if key.startswith(self.attr_prefix):
                            key = key.lstrip(self.attr_prefix)
                            # @xmlns: {$: xxx, svg: yyy} becomes xmlns="xxx" xmlns:svg="yyy"
                            if value_is_dict:
                                if self.lxml_lib:
                                    if key == self.ns_name.lstrip(self.attr_prefix):
                                        # Actually nothing to do here
                                        pass
                                else:
                                    for k in value.keys():
                                        if len(k) > 0:
                                            if k == self.text_content:
                                                k_default = 'ns0'
                                                self.ns_counter += 1
                                                result.set('xmlns:' + k_default, self._tostring(value[k]))
                                            else:
                                                result.set('xmlns:' + k, self._tostring(value[k]))
                                        else:
                                            result.set('xmlns' + k, self._tostring(value[k]))
                            else:
                                result.set(key, self._tostring(value))
                            continue
                    # Handle text content (BadgerFish, GData)
                    if self.text_content is not None:
                        if key == self.text_content:
                            result.text = self._tostring(value)
                            continue
                    # Treat scalars as text content, not children (GData)
                    if self.attr_prefix is None and self.text_content is not None:
                        if not value_is_dict and not value_is_list:
                            result.set(key, self._tostring(value))
                            continue
                # Add other keys as one or more children
                values = value if value_is_list else [value]
                for value in values:
                    if value_is_dict:
                        # Add namespaces to nodes if @xmlns present
                        if self.ns_name in value.keys() and self.lxml_lib:
                            NS_MAP = self.dict()
                            for k in value[self.ns_name]:
                                prefix = k
                                if prefix == self.text_content:
                                    prefix = 'ns0'
                                uri = value[self.ns_name][k]

                                if ':' in key:
                                    prefix, tag = key.split(':')
                                    key = tag

                                NS_MAP[prefix] = uri
                                continue

                            if len(value[self.ns_name]) > 1:
                                uri = ''
                            elem = self.element('{0}{1}'.format('{' + uri + '}', key), nsmap=NS_MAP)
                            result.append(elem)
                        else:
                            elem = self.element(key)
                            result.append(elem)
                    else:
                        elem = self.element(key)
                        result.append(elem)


                    # Treat scalars as text content, not children (Parker)
                    if not isinstance(value, (self.dict, dict, self.list, list)):
                        if self.text_content:
                            value = {self.text_content: value}
                    self.etree(value, root=elem)
        else:
            if self.text_content is None and root is not None:
                root.text = self._tostring(data)
            else:
                elem = self.element(self._tostring(data))
                if elem is not None:
                    result.append(elem)
        return result

    @staticmethod
    def _process_ns(cls, element):
        if element.tag.startswith('{'):
            if any([True if k.split(':')[0] == 'xmlns' else False for k in element.attrib.keys()]):
                revers_attr = {v:k for k,v in element.attrib.items()}

                end_prefix = element.tag.find('}')
                uri = element.tag[:end_prefix+1]
                key_prefix = revers_attr[uri.strip('{}')]
                prefix = key_prefix.split(':')[1]

                if len(prefix) > 1:
                    element.tag = element.tag.replace(uri, prefix + ':')
                else:
                    element.tag = element.tag.replace(uri, '')

                # trick to determine if given element is root element
                try:
                    _ = element.getroot()
                    element.attrib.pop(key_prefix, None)
                except:
                    pass
        else:
            ns_keys = [k if k.split(':')[0] == 'xmlns' else None for k in element.attrib.keys()]
            for key in ns_keys:
                if key:
                    element.attrib.pop(key, None)
        return element

    @classmethod
    def parse_nsmap(cls, file):
        # Parse given file-like xml object for namespaces
        if isinstance(file, (str)):
            file = BytesIO(file.encode('utf-8'))

        events = "start", "start-ns", "end-ns"
        root = None
        ns_map = []

        for event, elem in iterparse(file, events):
            if event == "start-ns":
                ns_map.append(elem)
            elif event == "end-ns":
                ns_map.pop()
            elif event == "start":
                if root is None:
                    root = elem
                if ns_map:
                    for ns in ns_map:
                        ns_prefix = ns[0]
                        ns_uri = ns[1]
                        elem.set('xmlns:{}'.format(ns_prefix), ns_uri)
        return ElementTree(root).getroot()


class BadgerFish(XMLData):
    '''Converts between XML and data using the BadgerFish convention'''
    def __init__(self, **kwargs):
        super(BadgerFish, self).__init__(attr_prefix='@', text_content='$', ns_name='@xmlns', **kwargs)

    # todo gucken wass ich noch in funktionen auslagern kann, um code übersichtlicher zu machen
    def data(self, root):

        '''Convert etree.Element into a dictionary'''
        value = self.dict() # create dict that represents the JSON Object
        children = [node for node in root if isinstance(node.tag, basestring)]  # list of all child elements

        # if typemapping is based on xml schema, search schema for element and get type
        if self.schema_typing:
            if self.is_doc_root:
                self.schema_element = self.xml_schema.elements[ET.QName(root).localname]
                self.root_schema_element = self.schema_element
                self.schema_stack.append(self.root_schema_element)

                # if attributes exist for element find the attributes in the schema
                if root.attrib.items():
                    self.schema_attribute_stack.append(self.root_schema_element)

            # todo kann das nicht nach unten verschieben, weil dort self.is_doc_root immer falsch ist,
            #  denn es wird im namespace teil gesetzt
            if (not self.is_doc_root) and root.text:
                self.schema_element = self.schema_stack.pop()
                schema_types = self.root_schema_element.type


        #---------------------------------------- NAMESPACE HANDLING --------------------------------------------------
        # if we want qualified Elementtags ("Person": {"@xmlns": {"null": "http://www.ncbi.nlm.nih.gov/geo/info/MINiML"})
        nsmap = root.nsmap
        if self.ns_as_attrib:
            root = XMLData._process_ns(self, element=root)
            # form lxml.Element with namespaces if present
            if self.lxml_lib:
                if root.tag.startswith('{'):
                    uri, root.tag = root.tag.split('}')
                    uri = uri.lstrip('{')
                    value[self.ns_name] = {}
                    # pushing namespaces to dic; Filtering namespaces by prefix except root node
                    for key in nsmap.keys():
                        if self.is_doc_root:
                            if key == None:
                                value[self.ns_name].update({self.text_content: nsmap[key]})
                            else:
                                value[self.ns_name].update({key: nsmap[key]})
                        else:
                            # check namespace prefix of xml element and write according namespace in json object
                            if nsmap[key] == uri:
                                if key == None:
                                    value[self.ns_name].update({self.text_content: nsmap[key]})
                                elif nsmap[key] == uri:
                                    value[self.ns_name].update({key: nsmap[key]})
                    self.is_doc_root = False
                else:
                    for attr, attrval in root.attrib.items():
                        attr = attr if self.attr_prefix is None else self.attr_prefix + attr
                        value[attr] = self._fromstring(attrval)


            # todo this is only relevant if we do not use lxml but xml -> just use lxml for my purposes
            else:
                for attr, attrval in root.attrib.items():
                    attr = attr if self.attr_prefix is None else self.attr_prefix + attr

                    if self.attr_prefix:
                        if self.ns_name in attr:
                            if not attr.endswith(':'):
                                prefix = attr.split(':')[1]
                                value[attr.replace(prefix, '')] = {prefix: self._fromstring(attrval)}
                            else:
                                prefix = attr.split(':')[1]
                                value['@xmlns'] = {prefix: self._fromstring(attrval)}
                        else:
                            value[attr] = self._fromstring(attrval)
                    else:
                        value[attr] = self._fromstring(attrval)
        # if we only want namespaces in root element # todo check if i can optimize this
        if not self.ns_as_attrib and self.is_doc_root:
            value[self.ns_name] = {}
            # clean up NS prefixes # todo hier könnte ich machen dass namespaces als prefixes verwendet werden
            for elem in root.getiterator():
                elem.tag = ET.QName(elem).localname
            for key in nsmap.keys():
                if key == None:
                    value[self.ns_name].update({self.text_content: nsmap[key]})
                    self.is_doc_root = False
                else:
                    value[self.ns_name].update({key: nsmap[key]})
            self.is_doc_root = False

        #--------------------------------------- ATTRIBUTE HANDLING --------------------------------------------------

        for attr, attrval in root.attrib.items():  # für alle attribute des  elementes
            # if schema_typing is used and the attribute exists in the schema
            if self.schema_typing:

                schema_att_element = self.schema_attribute_stack[-1]
                schema_types = schema_att_element.type
                schema_attributes = schema_types.attributes

                # if we find the attribute
                if schema_attributes.get(attr):
                # attribute types are always simple types
                    schema_attribute_type = schema_attributes.get(attr).type.base_type

                    attrval = self._typemapping(attrval, schema_attribute_type)
                    attr = attr if self.attr_prefix is None else self.attr_prefix + attr  # schreibe attribut plus prefix wenn es eins gibt
                    value[attr] = attrval  # value ist mein dict in dem ich die values speichere zu den attributen

            if not self.schema_typing:
                attr = attr if self.attr_prefix is None else self.attr_prefix + attr  # schreibe attribut plus prefix wenn es eins gibt
                value[attr] = self._fromstring(attrval)

        # remove the last item from attribute stack (only if we have attributes and stack is not empty)
        if self.schema_attribute_stack and root.attrib.items():
            self.schema_attribute_stack.pop()


        #-------------------------------------- TEXT HANDLING ---------------------------------------------------------
        if root.text and self.text_content is not None:
            text = root.text
            # if we can find a type
            if self.schema_typing and self.schema_element.type:

                schema_types = self.schema_element.type
                # if a simple type exists
                if schema_types.simple_type:
                    if text.strip():
                        # get simple type
                        schema_simple_type = schema_types.simple_type
                        # if a base type exists
                        if schema_types.simple_type.base_type:
                            schema_base_type = schema_types.simple_type.base_type
                            text = self._typemapping(text, schema_base_type)
                        else:
                            text = self._typemapping(text, schema_simple_type)

                        if self.simple_text and len(children) == len(root.attrib) == 0:
                            value = text
                        else:
                            value[self.text_content] = text

                        # previous element gets root schema element again
                        self.root_schema_element = self.schema_stack[-1]
            else:
                if text.strip():
                    if self.simple_text and len(children) == len(root.attrib) == 0:
                        value = self._fromstring(text)
                    else:
                        value[self.text_content] = self._fromstring(text)


        #------------------------------------- PROCESSING AND MOVING FURTHER IN TREE------------------------------------
        # merke, dass die tags alle noch den voll qualifizierten namen haben
        count = Counter(child.tag for child in children) # zählt das vorkommen der tags der kinder und eerzeugt dict (e.g. Sample:88)

        for child in children:
            schema_element_found = False
            # todo platzhalter für tests

            if self.schema_typing:
                # todo test: backtracke im schema bis element gefunden wurde
                #  (führt zu bug wenn kein passendes element existiert!) - da evtl noch was einbauen
                # muss diese archtitektur wählen da: ich keine objekte für jedes element habe in dem ich daten abspeicehrn aknn
                # muss über stack gehen und kann aber für die schema elemente nicht kinder abfragen -> gibt keinen weg abzufragen ob ich alle kinder abgearbeitet habe
                # kind array oder ähnliches kann ich so nicht speichern ohne klasse // grundaufbau des moduls ist dafür einfach nicht geeignet
                while not schema_element_found:
                    for i in self.root_schema_element:
                        if not self.ns_as_attrib:
                            if i.local_name == child.tag:
                                self.schema_stack.append(i)
                                self.root_schema_element = i

                                if child.attrib.items():
                                    self.schema_attribute_stack.append(i)

                                schema_element_found = True# break loop if match is found
                                break
                        if self.ns_as_attrib:
                            if i.name == child.tag:
                                self.schema_stack.append(i)
                                self.root_schema_element = i

                                if child.attrib.items():
                                    self.schema_attribute_stack.append(i)

                                schema_element_found = True  # break loop if match is found
                                break

                    if not schema_element_found:
                        # repeat for loop with next higher element if there is no match
                        self.schema_stack.pop()
                        self.root_schema_element = self.schema_stack[-1]


            if self.ns_as_attrib:
                child = XMLData._process_ns(self, child)

            # if abfrage hier ist dazu da um zu checken ob array gebraucht wird oder nicht
            if count[child.tag] == 1:
                value.update(self.data(child)) #neues element wird dictionary hinzugefügt, rekursiver funktionsaufruf

            else: #list() creates emtpy list
                result = value.setdefault(child.tag, self.list()) #setdefault: returns value of child.tag if it exists, if not create key and set value to self.list()
                result += self.data(child).values()

        # if simple_text, elements with no children nor attrs become '', not {}
        if isinstance(value, dict) and not value and self.simple_text:
            value = ''

        # hier wird der value für einen knoten ohne kinder geschrieben
        return self.dict([(root.tag, value)])

class GData(XMLData):
    '''Converts between XML and data using the GData convention'''
    def __init__(self, **kwargs):
        super(GData, self).__init__(text_content='$t', ns_name='xmlns', **kwargs)

    def data(self, root):

        '''Convert etree.Element into a dictionary'''
        '''Convert etree.Element into a dictionary'''
        value = self.dict() # create dict that represents the JSON Object
        children = [node for node in root if isinstance(node.tag, basestring)]  # list of all child elements
        print(self.schema_stack)
        # if typemapping is based on xml schema, search schema for element and get type
        if self.schema_typing:
            if self.is_doc_root:

                self.schema_element = self.xml_schema.elements[ET.QName(root).localname]
                self.root_schema_element = self.schema_element

                self.schema_stack.append(self.root_schema_element)
            #schema_types = schema_element.type
                # if attributes exist for element find the attributes in the schema
                if root.attrib.items():

                    self.schema_attribute_stack.append(self.root_schema_element)

            # todo kann das nicht nach unten verschieben, weil dort self.is_doc_root immer falsch ist,
            #  denn es wird im namespace teil gesetzt
            if (not self.is_doc_root) and root.text:
                self.schema_element = self.schema_stack.pop()
                schema_types = self.root_schema_element.type

        #---------------------------------------- NAMESPACE HANDLING --------------------------------------------------
        # if we want qualified Elementtags ("Person": {"@xmlns": {"null": "http://www.ncbi.nlm.nih.gov/geo/info/MINiML"})
        # get docinfo in first iteration

        nsmap = root.nsmap
        if self.ns_as_attrib:
            root = XMLData._process_ns(self, element=root)

            # form lxml.Element with namespaces if present
            if self.lxml_lib:
                if root.tag.startswith('{'): #if we find a namespace prefix that is (remember in lxml it's {uri}tagname}
                    uri, root.tag = root.tag.split('}') # split the tag into URIa nd Tagname #FIXME could use lxml Qname for that instead
                    uri = uri.lstrip('{') # free URI of leftover {
                    value[self.ns_name] = {}
                    # pushing namespaces to dic; Filtering namespaces by prefix except root node
                    for key in nsmap.keys():
                        if self.is_doc_root:
                            # if first key is namespace without suffix (=None)
                            if key == None:
                                value[self.ns_name] = nsmap[key]
                            # if first key is normal namespace
                            else:
                                ns_name = self.ns_name + "$" + key
                                value[ns_name] = nsmap[key]
                        else:
                            if nsmap[key] == uri:
                                if key == None:
                                    value[self.ns_name] = nsmap[key]
                                elif nsmap[key] == uri:
                                    ns_name = self.ns_name + "$" + key
                                    value[ns_name] = nsmap[key]
                    self.is_doc_root = False
                else:
                    for attr, attrval in root.attrib.items():
                        attr = attr if self.attr_prefix is None else self.attr_prefix + attr
                        value[attr] = self._fromstring(attrval)
            # todo this is only relevant if we do not use lxml but xml -> just use lxml for my purposes
            else:
                for attr, attrval in root.attrib.items():
                    attr = attr if self.attr_prefix is None else self.attr_prefix + attr

                    if self.attr_prefix:
                        if self.ns_name in attr:
                            if not attr.endswith(':'):
                                prefix = attr.split(':')[1]
                                value[attr.replace(prefix, '')] = {prefix: self._fromstring(attrval)}
                            else:
                                prefix = attr.split(':')[1]
                                value['@xmlns'] = {prefix: self._fromstring(attrval)}
                        else:
                            value[attr] = self._fromstring(attrval)
                    else:
                        value[attr] = self._fromstring(attrval)

        # if we only want namespaces in root element
        if not self.ns_as_attrib and self.is_doc_root:
            value[self.ns_name] = {}
            # clean up NS prefixes
            for elem in root.getiterator():
                elem.tag = ET.QName(elem).localname
            for key in nsmap.keys():
                if key == None:
                    value[self.ns_name] = nsmap[key]
                    self.is_doc_root = False
                else:
                    ns_name = self.ns_name + "$" + key
                    value[ns_name] = nsmap[key]
            self.is_doc_root = False

        # --------------------------------------------------------ATTRIBUTEHANDLING-------------------------------------
        for attr, attrval in root.attrib.items():  # für alle attribute des  elementes
            # if schema_typing is used and the attribute exists in the schema
            if self.schema_typing:

                schema_att_element = self.schema_attribute_stack[-1]
                schema_types = schema_att_element.type
                schema_attributes = schema_types.attributes

                # if we find the attribute
                if schema_attributes.get(attr):
                # attribute types are always simple types
                    schema_attribute_type = schema_attributes.get(attr).type.base_type

                    attrval = self._typemapping(attrval, schema_attribute_type)
                    attr = attr if self.attr_prefix is None else self.attr_prefix + attr  # schreibe attribut plus prefix wenn es eins gibt
                    value[attr] = attrval  # value ist mein dict in dem ich die values speichere zu den attributen

            if not self.schema_typing:
                attr = attr if self.attr_prefix is None else self.attr_prefix + attr  # schreibe attribut plus prefix wenn es eins gibt
                value[attr] = self._fromstring(attrval)

        # remove the last item from attribute stack (only if we have attributes and stack is not empty)
        if self.schema_attribute_stack and root.attrib.items():
            self.schema_attribute_stack.pop()

        #-------------------------------------- TEXT HANDLING ---------------------------------------------------------
        if root.text and self.text_content is not None:
            text = root.text
            # if we can find a type
            if self.schema_typing and self.schema_element.type:

                schema_types = self.schema_element.type
                # if a simple type exists
                if schema_types.simple_type:
                    if text.strip():
                        # get simple type
                        schema_simple_type = schema_types.simple_type
                        # if a base type exists
                        if schema_types.simple_type.base_type:
                            schema_base_type = schema_types.simple_type.base_type
                            text = self._typemapping(text, schema_base_type)
                        else:
                            text = self._typemapping(text, schema_simple_type)

                        if self.simple_text and len(children) == len(root.attrib) == 0:
                            value = text
                        else:
                            value[self.text_content] = text

                        # previous element gets root schema element again
                        self.root_schema_element = self.schema_stack[-1]
            else:
                if text.strip():
                    if self.simple_text and len(children) == len(root.attrib) == 0:
                        value = self._fromstring(text)
                    else:
                        value[self.text_content] = self._fromstring(text)


        # merke, dass die tags alle noch den voll qualifizierten namen haben
        count = Counter(child.tag for child in children) # zählt das vorkommen der tags der kinder und eerzeugt dict (e.g. Sample:88)
        for child in children:

            schema_element_found = False
            # todo platzhalter für tests


            if self.schema_typing:
                # todo test: backtracke im schema bis element gefunden wurde
                #  (führt zu bug wenn kein passendes element existiert!) - da evtl noch was einbauen
                # muss diese archtitektur wählen da: ich keine objekte für jedes element habe in dem ich daten abspeicehrn aknn
                # muss über stack gehen und kann aber für die schema elemente nicht kinder abfragen -> gibt keinen weg abzufragen ob ich alle kinder abgearbeitet habe
                # kind array oder ähnliches kann ich so nicht speichern ohne klasse // grundaufbau des moduls ist dafür einfach nicht geeignet
                while not schema_element_found:
                    for i in self.root_schema_element:
                        if not self.ns_as_attrib:
                            if i.local_name == child.tag:
                                self.schema_stack.append(i)
                                self.root_schema_element = i

                                if child.attrib.items():
                                    self.schema_attribute_stack.append(i)

                                schema_element_found = True# break loop if match is found
                                break
                        if self.ns_as_attrib:
                            if i.name == child.tag:
                                self.schema_stack.append(i)
                                self.root_schema_element = i

                                if child.attrib.items():
                                    self.schema_attribute_stack.append(i)

                                schema_element_found = True  # break loop if match is found
                                break
                    if not schema_element_found:
                        # repeat for loop with next higher element if there is no match
                        self.schema_stack.pop()
                        self.root_schema_element = self.schema_stack[-1]

            # if abfrage hier ist dazu da um zu checken ob array gebraucht wird oder nicht
            if self.ns_as_attrib:
                child = XMLData._process_ns(self, child)
            if count[child.tag] == 1:
                value.update(self.data(child)) #neues element wird dictionary hinzugefügt, rekursiver funktionsaufruf
            else: #list() creates emtpy list
                result = value.setdefault(child.tag, self.list()) #setdefault: returns value of child.tag if it exists, if not create key and set value to self.list()
                result += self.data(child).values()
        # if simple_text, elements with no children nor attrs become '', not {}
        if isinstance(value, dict) and not value and self.simple_text:
            value = ''

        return self.dict([(root.tag, value)])


class Yahoo(XMLData):
    '''Converts between XML and data using the Yahoo convention'''
    def __init__(self, **kwargs):
        kwargs.setdefault('xml_fromstring', False)
        super(Yahoo, self).__init__(text_content='content', simple_text=True, **kwargs)


class Parker(XMLData):
    '''Converts between XML and data using the Parker convention'''
    def __init__(self, **kwargs):
        self.schema_stack = []
        super(Parker, self).__init__(**kwargs)


    def data(self, root, preserve_root=False):
        '''Convert etree.Element into a dictionary'''
        # If preserve_root is False, return the root element. This is easiest
        # done by wrapping the XML in a dummy root element that will be ignored.
        #print(self.schema_stack)
        # if typemapping is based on xml schema, search schema for element and get type
        if self.schema_typing:
            if self.is_doc_root:
                self.schema_element = self.xml_schema.elements[ET.QName(root).localname]
                self.root_schema_element = self.schema_element
                self.schema_stack.append(self.root_schema_element)


            # todo kann das nicht nach unten verschieben, weil dort self.is_doc_root immer falsch ist,
            #  denn es wird im namespace teil gesetzt
            if (not self.is_doc_root) and root.text:
                self.schema_element = self.schema_stack.pop()
                schema_types = self.root_schema_element.type

            self.is_doc_root = False

        if preserve_root:
            new_root = root.makeelement('dummy_root', {})
            new_root.insert(0, root)
            root = new_root


        children = [node for node in root if isinstance(node.tag, basestring)]
        # If no children, just return the text
        if len(children) == 0:
            if self.schema_typing and self.schema_element.type:
                schema_types = self.schema_element.type
                # if a simple type exists
                if schema_types.simple_type:
                        # get simple type
                    schema_simple_type = schema_types.simple_type
                        # if a base type exists
                    if schema_types.simple_type.base_type:
                        schema_base_type = schema_types.simple_type.base_type
                        text = self._typemapping(root.text, schema_base_type)
                    else:
                        text = self._typemapping(root.text, schema_simple_type)

                        # previous element gets root schema element again
                    self.root_schema_element = self.schema_stack[-1]

                    return text
                else:
                    return self._fromstring(root.text)

            else:
                return self._fromstring(root.text)

        # Element names become object properties
        count = Counter(child.tag for child in children)
        result = self.dict()


        for child in children:
            schema_element_found = False
            # todo platzhalter für tests
            if self.schema_typing:
                # todo test: backtracke im schema bis element gefunden wurde
                #  (führt zu bug wenn kein passendes element existiert!) - da evtl noch was einbauen
                # muss diese archtitektur wählen da: ich keine objekte für jedes element habe in dem ich daten abspeicehrn aknn
                # muss über stack gehen und kann aber für die schema elemente nicht kinder abfragen -> gibt keinen weg abzufragen ob ich alle kinder abgearbeitet habe
                # kind array oder ähnliches kann ich so nicht speichern ohne klasse // grundaufbau des moduls ist dafür einfach nicht geeignet
                while not schema_element_found:
                    for i in self.root_schema_element:
                        if i.name == child.tag:
                            self.schema_stack.append(i)
                            self.root_schema_element = i
                            schema_element_found = True  # break loop if match is found
                            break
                    if not schema_element_found:
                        # repeat for loop with next higher element if there is no match
                        self.schema_stack.pop()
                        self.root_schema_element = self.schema_stack[-1]

            if count[child.tag] == 1:
                result[child.tag] = self.data(child)
            else:
                result.setdefault(child.tag, self.list()).append(self.data(child))

        return result


class Abdera(XMLData):
    '''Converts between XML and data using the Abdera convention'''
    def __init__(self, **kwargs):
        super(Abdera, self).__init__(simple_text=True, text_content=True, **kwargs)

    def data(self, root):
        '''Convert etree.Element into a dictionary'''
        value = self.dict()

        if self.schema_typing:
            if self.is_doc_root:
                self.schema_element = self.xml_schema.elements[ET.QName(root).localname]
                self.root_schema_element = self.schema_element
                self.schema_stack.append(self.root_schema_element)

                # if attributes exist for element find the attributes in the schema
                if root.attrib.items():
                    self.schema_attribute_stack.append(self.root_schema_element)

            if (not self.is_doc_root) and root.text:
                self.schema_element = self.schema_stack.pop()
                schema_types = self.root_schema_element.type

            self.is_doc_root = False


        # Add attributes specific 'attributes' key
        if root.attrib:
            value['attributes'] = self.dict()
            for attr, attrval in root.attrib.items():

                if self.schema_typing:

                    schema_att_element = self.schema_attribute_stack[-1]
                    schema_types = schema_att_element.type
                    schema_attributes = schema_types.attributes

                    # if we find the attribute
                    if schema_attributes.get(attr):
                        # attribute types are always simple types
                        schema_attribute_type = schema_attributes.get(attr).type.base_type
                        attrval = self._typemapping(attrval, schema_attribute_type)
                        value['attributes'][unicode(attr)] = attrval

                if not self.schema_typing:
                    value['attributes'][unicode(attr)] = self._fromstring(attrval)

        # remove the last item from attribute stack (only if we have attributes and stack is not empty)
        if self.schema_attribute_stack and root.attrib.items():
            self.schema_attribute_stack.pop()


        # Add children to specific 'children' key
        children_list = self.list()
        children = [node for node in root if isinstance(node.tag, basestring)]

        # Add root text
        if root.text and self.text_content is not None:
            text = root.text

            if self.schema_typing and self.schema_element.type:
                schema_types = self.schema_element.type
                # if a simple type exists
                if schema_types.simple_type:
                    if text.strip():
                        # get simple type
                        schema_simple_type = schema_types.simple_type
                        # if a base type exists
                        if schema_types.simple_type.base_type:
                            schema_base_type = schema_types.simple_type.base_type
                            text = self._typemapping(text, schema_base_type)
                        else:
                            text = self._typemapping(text, schema_simple_type)

                        if self.simple_text and len(children) == len(root.attrib) == 0:
                            value = text
                        else:
                            children_list = [text, ]

                        # previous element gets root schema element again
                        self.root_schema_element = self.schema_stack[-1]
            else:
                if text.strip():
                    if self.simple_text and len(children) == len(root.attrib) == 0:
                        value = self._fromstring(text)
                    else:
                        children_list = [self._fromstring(text), ]


        for child in children:
            schema_element_found = False
            # todo platzhalter für tests

            if self.schema_typing:
                # todo test: backtracke im schema bis element gefunden wurde
                #  (führt zu bug wenn kein passendes element existiert!) - da evtl noch was einbauen
                # muss diese archtitektur wählen da: ich keine objekte für jedes element habe in dem ich daten abspeicehrn aknn
                # muss über stack gehen und kann aber für die schema elemente nicht kinder abfragen -> gibt keinen weg abzufragen ob ich alle kinder abgearbeitet habe
                # kind array oder ähnliches kann ich so nicht speichern ohne klasse // grundaufbau des moduls ist dafür einfach nicht geeignet
                while not schema_element_found:
                    for i in self.root_schema_element:
                        if i.name == child.tag:
                            self.schema_stack.append(i)
                            self.root_schema_element = i
                            if child.attrib.items():
                                self.schema_attribute_stack.append(i)
                            schema_element_found = True  # break loop if match is found
                            break

                    if not schema_element_found:
                        # repeat for loop with next higher element if there is no match
                        self.schema_stack.pop()
                        self.root_schema_element = self.schema_stack[-1]

            child_data = self.data(child)
            children_list.append(child_data)

        # Flatten children
        if len(root.attrib) == 0 and len(children_list) == 1:
            value = children_list[0]

        elif len(children_list) > 0:
            value['children'] = children_list

        return self.dict([(unicode(root.tag), value)])


# The difference between Cobra and Abdera is that Cobra _always_ has 'attributes' keys,
# 'children' key is remove when only one child and everything is a string.
# https://github.com/datacenter/cobra/blob/master/cobra/internal/codec/jsoncodec.py
class Cobra(XMLData):
    '''Converts between XML and data using the Cobra convention'''
    def __init__(self, **kwargs):
        super(Cobra, self).__init__(simple_text=True, text_content=True,
                                    xml_fromstring=False, **kwargs)

    def etree(self, data, root=None):
        '''Convert data structure into a list of etree.Element'''
        result = self.list() if root is None else root
        if isinstance(data, (self.dict, dict)):
            for key, value in data.items():
                if isinstance(value, (self.dict, dict)):
                    elem = self.element(key)
                    if elem is None:
                        continue
                    result.append(elem)

                    if 'attributes' in value:
                        for k, v in value['attributes'].items():
                            elem.set(k, self._tostring(v))
                    # else:
                    #     raise ValueError('Cobra requires "attributes" key for each element')

                    if 'children' in value:
                        for v in value['children']:
                            self.etree(v, root=elem)
                else:
                    elem = self.element(key)
                    if elem is None:
                        continue
                    elem.text = self._tostring(value)
                    result.append(elem)
        else:
            if root is not None:
                root.text = self._tostring(data)
            else:
                elem = self.element(self._tostring(data))
                if elem is not None:
                    result.append(elem)

        return result

    def data(self, root):
        '''Convert etree.Element into a dictionary'''

        value = self.dict()

        # Add attributes to 'attributes' key (sorted!) even when empty
        value['attributes'] = self.dict()
        if root.attrib:
            for attr in sorted(root.attrib):
                value['attributes'][unicode(attr)] = root.attrib[attr]

        # Add children to specific 'children' key
        children_list = self.list()
        children = [node for node in root if isinstance(node.tag, basestring)]

        # Add root text
        if root.text and self.text_content is not None:
            text = root.text
            if text.strip():
                if self.simple_text and len(children) == len(root.attrib) == 0:
                    value = self._fromstring(text)
                else:
                    children_list = [self._fromstring(text), ]

        count = Counter(child.tag for child in children)
        for child in children:
            child_data = self.data(child)
            if (count[child.tag] == 1 and
                len(children_list) > 1 and
                isinstance(children_list[-1], dict)):
                # Merge keys to existing dictionary
                children_list[-1].update(child_data)
            else:
                # Add additional text
                children_list.append(self.data(child))

        if len(children_list) > 0:
            value['children'] = children_list

        return self.dict([(unicode(root.tag), value)])


abdera = Abdera()
badgerfish = BadgerFish()
cobra = Cobra()
gdata = GData()
parker = Parker()
#yahoo = Yahoo()
