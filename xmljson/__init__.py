# -*- coding: utf-8 -*-

import sys
from collections import Counter, OrderedDict
from io import BytesIO

import lxml.etree as ET
import xmlschema

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


# this fork does only work with lxml.etree
# to make it work with xml.etree adjustments have to made: i.e. splitting into ns-prefix and tag has to be done
# with split function, since QName(elem) is not available in etree
class XMLData(object):
    def __init__(self, xml_fromstring=True, xml_tostring=True, element=None, dict_type=None,
                 list_type=None, attr_prefix=None, text_content=None, simple_text=False, ns_name=None,
                 ns_as_attrib=None, ns_as_prefix=None, invalid_tags=None, xml_schema=None, conv=None):
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
        # True if Namespaces should be used as attribute values (default True)
        self.ns_as_attrib = ns_as_attrib
        # True if Names should be prefixed by namespace (default False)
        self.ns_as_prefix = ns_as_prefix

        # True if root element hasn't been visited
        self.is_doc_root = True

        # store current root of (partial) schema tree in which we look for schema_element
        self.root_schema_element = None
        # store the current schema element
        self.schema_element = None
        # true if schema_element has been found
        self.schema_element_found = False
        # used for schema traversal / remembering position in schema
        self.schema_stack = []
        self.schema_attribute_stack = []

        self.lxml_lib = True

        # used to identify convention
        self.conv = conv

        #  use schema to infer type / only works for Abdera, Badgerfish, Gdata and Parker
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
        if value is None:
            pass
        else:
            value = str(value)
        return unicode(value)  # noqa: convert to whatever native unicode repr

    @staticmethod
    def _typemapping(content, xsd_type):
        '''Convert content to json types according to mapping of xsd_simpletype'''

        convert_to_string = ["XsdAtomicBuiltin(name='xs:ID')", "XsdAtomicBuiltin(name='xs:string')",
                             "XsdAtomicBuiltin(name='xs:normalizedString')",
                             "XsdAtomicBuiltin(name='xs:date')", "XsdAtomicBuiltin(name='xs:time')",
                             "XsdAtomicBuiltin(name='xs:anyURI')", "XsdAtomicBuiltin(name='xs:token')",
                             "XsdAtomicBuiltin(name='xs:IDREF')", "XsdAtomicBuiltin(name='xs:NCName')"]
        convert_to_int = ["XsdAtomicBuiltin(name='xs:positiveInteger')",
                          "XsdAtomicBuiltin(name='xs:nonNegativeInteger')",
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
        # why value.lower()? => makes test case fail cause 0.0M gets 0.0m for example
        try:

            if value.lower().startswith('0'):
                return value
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

    def data(self, root):
        '''Convert etree.Element into a dictionary. Used for Badgerfish and GData, other conventions overwrite this function
        '''

        value = self.dict()  # create dict that represents the JSON Object
        children = [node for node in root if isinstance(node.tag, basestring)]  # list of all child elements
        tag = ET.QName(root).localname
        nsmap = root.nsmap

        # if typemapping is based on xml schema initialize stack and manage it
        if self.schema_typing:
            self._manage_schema_stack(root)

        # if object has a namespace process them (as attribute or not, depending on ns_as_attribute)
        if ET.QName(root).namespace:
            # root = XMLData._process_ns(self, element=root)
            value = self._process_namespace(root, value)

        self.is_doc_root = False
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

        # -------------------------------------- TEXT HANDLING ---------------------------------------------------------
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
        count = Counter(child.tag for child in
                        children)  # zählt das vorkommen der tags der kinder und eerzeugt dict (e.g. Sample:88)
        for child in children:
            if self.schema_typing:
                self._find_schema_element(child)
            # if abfrage hier ist dazu da um zu checken ob array gebraucht wird oder nicht
            if self.ns_as_attrib:
                child = XMLData._process_ns(self, child)
            if count[child.tag] == 1:
                value.update(self.data(child))  # neues element wird dictionary hinzugefügt, rekursiver funktionsaufruf
            else:  # list() creates emtpy list
                if not self.ns_as_prefix:
                    child_tag = ET.QName(child).localname
                elif self.ns_as_prefix:
                    # use first one if prefixes, second one if uri
                    child_tag = self._uri_to_prefix(child.tag, nsmap)
                    # child_tag = child.tag
                # setdefault: returns value of child.tag if it exists, if not create key and set value to self.list()

                result = value.setdefault(child_tag,
                                          self.list())
                result += self.data(child).values()

        # if simple_text, elements with no children nor attrs become '', not {}
        if isinstance(value, dict) and not value and self.simple_text:
            value = ''

        # hier wird der value für einen knoten ohne kinder geschrieben
        # if we do not want prefixed objectnames
        if not self.ns_as_prefix:
            return self.dict([(tag, value)])
        # if we want prefixed objectnames
        if self.ns_as_prefix:
            # use this function if prefix abbr. and not uris are wanted
            tag = self._uri_to_prefix(root.tag, nsmap)
            return self.dict([(tag, value)])
            # use this if uris as prefix are wanted
            # return self.dict([(root.tag, value)])

    def etree(self, data, root=None):
        '''Convert data structure into a list of etree.Element'''
        '''Fails if namespace handling is customized and deviates from convention standard'''
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
                                    # no prefix for standardnamespace (xml convention)
                                    prefix = None
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
                if data == None:
                    pass
                else:
                    root.text = self._tostring(data)

            else:
                elem = self.element(self._tostring(data))
                if elem is not None:
                    result.append(elem)
        return result

    @staticmethod
    def _process_ns(cls, element):
        # todo checken wofür das ist
        if element.tag.startswith('{'):
            # process attribute namespaces // für normale elemente bleibt es hier stehen
            if any([True if k.split(':')[0] == 'xmlns' else False for k in element.attrib.keys()]):

                revers_attr = {v: k for k, v in element.attrib.items()}

                end_prefix = element.tag.find('}')
                uri = element.tag[:end_prefix + 1]
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

    def _find_schema_element(self, xmlelement):
        """search schema for fitting element for xmlelement
        self.schema_stack contains all visited elements that have not yet been found
        self.root_schemaelement is the root of the current subtree. Helper function for converters."""
        # todo define what to do if element cant be found

        self.schema_element_found = False
        while not self.schema_element_found:
            for i in self.root_schema_element:
                if i.name == xmlelement.tag:
                    self.schema_stack.append(i)
                    self.root_schema_element = i
                    if xmlelement.attrib.items():
                        self.schema_attribute_stack.append(i)
                    self.schema_element_found = True  # break loop if match is found
                    break
            if not self.schema_element_found:
                # repeat for loop with next higher element if there is no match
                self.schema_stack.pop()
                self.root_schema_element = self.schema_stack[-1]

    def _manage_schema_stack(self, root):
        """initialize schema stack and remove elements if needed"""
        if self.is_doc_root:
            self.schema_element = self.xml_schema.elements[ET.QName(root).localname]
            self.root_schema_element = self.schema_element
            self.schema_stack.append(self.root_schema_element)
            # if attributes exist for element find the attributes in the schema
            if root.attrib.items():
                self.schema_attribute_stack.append(self.root_schema_element)

        # todo: erklärung => dieser teil ist eigentlich redundant, da in _find_schema_element auch das element gepoppt wird
        # allerdings erst nach einer schleife, dies kann hierdurch vermieden werden
        elif root.text:
            self.schema_element = self.schema_stack.pop()

        # todo implement handling of elements with text and children -> doesn't work yet
    def _process_namespace(self, root, value):
        """create namespace object in root and namespaces attribute objects, if ns_as_attrib = True
        Only used in badgerfish and gdata. Other conventions skip namespaces."""
        nsmap = root.nsmap
        uri = ET.QName(root).namespace
        # split namespace uri and tag
        # pushing namespaces to dict; Filtering namespaces by prefix except root node
        if self.is_doc_root:
            # initialize namespace object
            value[self.ns_name] = {}
            for key in nsmap.keys():
                if key == None:
                    if self.conv == "badgerfish":
                        # enter standard namespace into toplevel namespace obj
                        value[self.ns_name].update({self.text_content: nsmap[key]})
                    elif self.conv == "gdata":
                        value[self.ns_name] = nsmap[key]
                else:
                    if self.conv == "badgerfish":
                        # enter standard namespace into toplevel namespace obj
                        value[self.ns_name].update({key: nsmap[key]})
                    elif self.conv == "gdata":
                        ns_name = self.ns_name + "$" + key
                        value[ns_name] = nsmap[key]
                    # enter other namespaces into toplevel namespace obj
        # if we want namespaces as JSON attributes
        elif self.ns_as_attrib:
            # initialize namespace object
            # todo ich glaube das will ich nur wenn ich badgerfish habe oder
            value[self.ns_name] = {}
            for key in nsmap.keys():
                # check namespace prefix of xml element and write according namespace in json object
                # could add the option here to leave out standard namespace / but badgerfish explicitely doesnt leave it out
                if nsmap[key] == uri:
                    if key == None:
                        if self.conv == "badgerfish":
                            # enter standard namespace into toplevel namespace obj
                            value[self.ns_name].update({self.text_content: nsmap[key]})
                        elif self.conv == "gdata":
                            value[self.ns_name] = nsmap[key]
                    else:
                        if self.conv == "badgerfish":
                            # enter standard namespace into toplevel namespace obj
                            value[self.ns_name].update({key: nsmap[key]})
                        elif self.conv == "gdata":
                            ns_name = self.ns_name + "$" + key
                            value[ns_name] = nsmap[key]
                            del value[self.ns_name]  # delete old key (standard ns, since its empty)

        # print(value)
        return value

    def _uri_to_prefix(self, tag, nsmap):
        """changes prefix of prefixed tag from URI to prefix"""
        # takes root.tag from lxml.etree
        nsmap_uri = {}
        uri = ET.QName(tag).namespace
        tag = ET.QName(tag).localname
        for ns_prefix in nsmap.keys():
            ns_uri = nsmap[ns_prefix]
            nsmap_uri[ns_uri] = ns_prefix

        for ns_uri in nsmap_uri.keys():
            if ns_uri == uri:
                # standard namespace, do not prefix in this case (xml convention)
                if nsmap_uri[ns_uri] == None:
                    pass
                else:
                    if self.conv == "gdata":
                        tag = nsmap_uri[uri] + "$" + tag  # prefix namespace tag
                    else:
                        tag = nsmap_uri[uri] + ":" + tag  # prefix namespace tag
                return tag

        # if no namespace can be found for the tag return without
        return tag


class BadgerFish(XMLData):
    '''Converts between XML and data using the BadgerFish convention. Conversion back to XML only possible with default namespace Handling.'''

    def __init__(self, ns_as_attrib=True, ns_as_prefix=False, **kwargs):
        super(BadgerFish, self).__init__(attr_prefix='@', text_content='$', ns_name='@xmlns', ns_as_attrib=ns_as_attrib,
                                         ns_as_prefix=ns_as_prefix,
                                         conv="badgerfish", **kwargs)


class GData(XMLData):
    '''Converts between XML and data using the GData convention. Conversion back to XML only possible with default namespace Handling.'''

    def __init__(self, ns_as_attrib=False, ns_as_prefix=True, **kwargs):
        super(GData, self).__init__(text_content='$t', ns_name='xmlns', conv="gdata", ns_as_attrib=ns_as_attrib,
                                    ns_as_prefix=ns_as_prefix, **kwargs)


class Parker(XMLData):
    '''Converts between XML and data using the Parker convention.'''

    def __init__(self, ns_as_prefix=True, **kwargs):
        super(Parker, self).__init__(ns_as_attrib=False, conv="parker", ns_as_prefix=ns_as_prefix, **kwargs)

    def data(self, root, preserve_root=False):
        '''Convert etree.Element into a dictionary'''
        # If preserve_root is False, return the root element. This is easiest
        # done by wrapping the XML in a dummy root element that will be ignored.
        # print(self.schema_stack)
        # if typemapping is based on xml schema, search schema for element and get type
        nsmap = root.nsmap
        tag = root.tag
        if self.schema_typing:
            self._manage_schema_stack(root)

        if preserve_root:
            new_root = root.makeelement('dummy_root', {})
            new_root.insert(0, root)
            root = new_root

        self.is_doc_root = False
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

            if self.schema_typing:
                self._find_schema_element(child)

            if not self.ns_as_prefix:
                tag = ET.QName(child).localname

            if self.ns_as_prefix:
                # todo comment and uncomment here if URI instead of prefixes
                tag = child.tag  # use this if uris as prefix
            #    tag = self._uri_to_prefix(child.tag, nsmap) #use this if prefix

            if count[child.tag] == 1:
                result[tag] = self.data(child)
            else:
                result.setdefault(tag, self.list()).append(self.data(child))

        return result


class Abdera(XMLData):
    '''Converts between XML and data using the Abdera convention'''

    def __init__(self, ns_as_prefix=True, **kwargs):
        super(Abdera, self).__init__(simple_text=True, text_content=True, ns_as_attrib=False, conv="abdera",
                                     ns_as_prefix=ns_as_prefix, **kwargs)

    def data(self, root):
        '''Convert etree.Element into a dictionary'''
        value = self.dict()
        tag = ET.QName(root).localname
        nsmap = root.nsmap
        if self.schema_typing:
            self._manage_schema_stack(root)

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

            if self.schema_typing:
                self._find_schema_element(child)

            child_data = self.data(child)
            children_list.append(child_data)

        # Flatten children
        if len(root.attrib) == 0 and len(children_list) == 1:
            value = children_list[0]

        elif len(children_list) > 0:
            value['children'] = children_list

        # if we do not want prefixed objectnames
        if not self.ns_as_prefix:
            return self.dict([(unicode(tag), value)])
        # if we want prefixed objectnames
        if self.ns_as_prefix:
            # use this function if prefix abbr. and not uris are wanted
            tag = self._uri_to_prefix(root.tag, nsmap)
            # use this if uris as prefix are wanted
            # tag = root.tag
            return self.dict([(unicode(tag), value)])


# The difference between Cobra and Abdera is that Cobra _always_ has 'attributes' keys,
# 'children' key is remove when only one child and everything is a string.
# https://github.com/datacenter/cobra/blob/master/cobra/internal/codec/jsoncodec.py
class Cobra(XMLData):
    '''Converts between XML and data using the Cobra convention'''

    def __init__(self, ns_as_prefix=True, **kwargs):
        super(Cobra, self).__init__(simple_text=True, text_content=True,
                                    xml_fromstring=False, ns_as_attrib=False, conv="cobra", ns_as_prefix=ns_as_prefix,
                                    **kwargs)

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
        nsmap = root.nsmap
        tag = ET.QName(root).localname

        # if typemapping is based on xml schema, search schema for element and get type
        if self.schema_typing:
            self._manage_schema_stack(root)

        self.is_doc_root = False

        # Add attributes to 'attributes' key (sorted!) even when empty
        value['attributes'] = self.dict()
        if root.attrib:
            for attr in sorted(root.attrib):
                # if schema_typing is used and the attribute exists in the schema
                if self.schema_typing:
                    schema_att_element = self.schema_attribute_stack[-1]
                    schema_types = schema_att_element.type
                    schema_attributes = schema_types.attributes
                    # if we find the attribute
                    if schema_attributes.get(attr):
                        # attribute types are always simple types
                        schema_attribute_type = schema_attributes.get(attr).type.base_type
                        attrval = self._typemapping(root.attrib[attr], schema_attribute_type)
                        value['attributes'][unicode(attr)] = attrval

                if not self.schema_typing:
                    value['attributes'][unicode(attr)] = root.attrib[attr]

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
                            value[self.text_content] = text
                            children_list = [text, ]
                        # previous element gets root schema element again
                        self.root_schema_element = self.schema_stack[-1]

            else:
                if text.strip():
                    if self.simple_text and len(children) == len(root.attrib) == 0:
                        value = self._fromstring(text)
                    else:
                        children_list = [self._fromstring(text), ]

        count = Counter(child.tag for child in children)
        for child in children:

            if self.schema_typing:
                self._find_schema_element(child)

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

        # if we do not want prefixed objectnames
        if not self.ns_as_prefix:
            return self.dict([(unicode(tag), value)])
        # if we want prefixed objectnames
        if self.ns_as_prefix:
            # use this function if prefix abbr. and not uris are wanted
            tag = self._uri_to_prefix(root.tag, nsmap)
            # use this if uris as prefix are wanted
            # tag = root.tag
            return self.dict([(unicode(tag), value)])


class Yahoo(XMLData):
    '''Converts between XML and data using the Yahoo convention'''

    def __init__(self, **kwargs):
        kwargs.setdefault('xml_fromstring', False)
        super(Yahoo, self).__init__(text_content='content', simple_text=True, conv="yahoo")


abdera = Abdera()
badgerfish = BadgerFish()
cobra = Cobra()
gdata = GData()
parker = Parker()
yahoo = Yahoo()
