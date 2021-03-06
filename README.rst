===============================
xmljson - Fork for MINiML-Documents. 
===============================
Small changes to conventions, namespace support for XML-to-JSON-mappings, schema checking for datatype mapping and optional MINiML-Datacleaning in the transformation process have been added.
-------------------------------

.. image:: https://img.shields.io/travis/sanand0/xmljson.svg
        :target: https://travis-ci.org/sanand0/xmljson

.. image:: https://img.shields.io/pypi/v/xmljson.svg
        :target: https://pypi.python.org/pypi/xmljson

This library is not actively maintained. Alternatives are `xmltodict`_ and `untangle`_.
Use only if you need to parse using specific XML to JSON `conventions`_.

.. _conventions: http://wiki.open311.org/JSON_and_XML_Conversion/
.. _xmltodict: https://github.com/martinblech/xmltodict
.. _untangle: https://untangle.readthedocs.io/en/latest/

xmljson converts XML into Python dictionary structures (trees, like in JSON) and vice-versa.

About
-----

XML can be converted to a data structure (such as JSON) and back. For example::

    <employees>
        <person>
            <name value="Alice"/>
        </person>
        <person>
            <name value="Bob"/>
        </person>
    </employees>

can be converted into this data structure (which also a valid JSON object)::

    {
        "employees": [{
            "person": {
                "name": {
                    "@value": "Alice"
                }
            }
        }, {
            "person": {
                "name": {
                    "@value": "Bob"
                }
            }
        }]
    }

This uses the `BadgerFish`_ convention that prefixes attributes with ``@``.
The conventions supported by this library are:

* `Abdera`_: Use ``"attributes"`` for attributes, ``"children"`` for nodes
* `BadgerFish`_: Use ``"$"`` for text content, ``@`` to prefix attributes
* `Cobra`_: Use ``"attributes"`` for sorted attributes (even when empty), ``"children"`` for nodes, values are strings
* `GData`_: Use ``"$t"`` for text content, attributes added as-is
* `Parker`_: Use tail nodes for text content, ignore attributes
* `Yahoo`_ Use ``"content"`` for text content, attributes added as-is

.. _Abdera: http://wiki.open311.org/JSON_and_XML_Conversion/#the-abdera-convention
.. _BadgerFish: http://www.sklar.com/badgerfish/
.. _Cobra: http://wiki.open311.org/JSON_and_XML_Conversion/#the-cobra-convention
.. _GData: http://wiki.open311.org/JSON_and_XML_Conversion/#the-gdata-convention
.. _Parker: https://developer.mozilla.org/en-US/docs/JXON#The_Parker_Convention
.. _Yahoo: https://developer.yahoo.com/javascript/json.html#xml


Convert data to XML
-------------------

To convert from a data structure to XML using the BadgerFish convention::

    >>> from xmljson import badgerfish as bf
    >>> bf.etree({'p': {'@id': 'main', '$': 'Hello', 'b': 'bold'}})

This returns an **array** of `etree.Element`_ structures. In this case, the
result is identical to::

    >>> from xml.etree.ElementTree import fromstring
    >>> [fromstring('<p id="main">Hello<b>bold</b></p>')]

.. _etree.Element: http://effbot.org/zone/element-index.htm

The result can be inserted into any existing root `etree.Element`_::

    >>> from xml.etree.ElementTree import Element, tostring
    >>> result = bf.etree({'p': {'@id': 'main'}}, root=Element('root'))
    >>> tostring(result)
    '<root><p id="main"/></root>'

This includes `lxml.html <http://lxml.de/lxmlhtml.html>`_ as well::

    >>> from lxml.html import Element, tostring
    >>> result = bf.etree({'p': {'@id': 'main'}}, root=Element('html'))
    >>> tostring(result, doctype='<!DOCTYPE html>')
    '<!DOCTYPE html>\n<html><p id="main"></p></html>'

For ease of use, strings are treated as node text. For example, both the
following are the same::

    >>> bf.etree({'p': {'$': 'paragraph text'}})
    >>> bf.etree({'p': 'paragraph text'})

By default, non-string values are converted to strings using Python's ``str``,
except for booleans -- which are converted into ``true`` and ``false`` (lower
case). Override this behaviour using ``xml_fromstring``::

    >>> tostring(bf.etree({'x': 1.23, 'y': True}, root=Element('root')))
    '<root><y>true</y><x>1.23</x></root>'
    >>> from xmljson import BadgerFish              # import the class
    >>> bf_str = BadgerFish(xml_tostring=str)       # convert using str()
    >>> tostring(bf_str.etree({'x': 1.23, 'y': True}, root=Element('root')))
    '<root><y>True</y><x>1.23</x></root>'

If the data contains invalid XML keys, these can be dropped via
``invalid_tags='drop'`` in the constructor::

    >>> bf_drop = BadgerFish(invalid_tags='drop')
    >>> data = bf_drop.etree({'$': '1', 'x': '1'}, root=Element('root'))    # Drops invalid <$> tag
    >>> tostring(data)
    '<root>1<x>1</x></root>'


Convert XML to data
-------------------

To convert from XML to a data structure using the BadgerFish convention::

    >>> bf.data(fromstring('<p id="main">Hello<b>bold</b></p>'))
    {"p": {"$": "Hello", "@id": "main", "b": {"$": "bold"}}}

To convert this to JSON, use::

    >>> from json import dumps
    >>> dumps(bf.data(fromstring('<p id="main">Hello<b>bold</b></p>')))
    '{"p": {"b": {"$": "bold"}, "@id": "main", "$": "Hello"}}'

To preserve the order of attributes and children, specify the ``dict_type`` as
``OrderedDict`` (or any other dictionary-like type) in the constructor::

    >>> from collections import OrderedDict
    >>> from xmljson import BadgerFish              # import the class
    >>> bf = BadgerFish(dict_type=OrderedDict)      # pick dict class

By default, values are parsed into boolean, int or float where possible (except
in the Yahoo method). Override this behaviour using ``xml_fromstring``::

    >>> dumps(bf.data(fromstring('<x>1</x>')))
    '{"x": {"$": 1}}'
    >>> bf_str = BadgerFish(xml_fromstring=False)   # Keep XML values as strings
    >>> dumps(bf_str.data(fromstring('<x>1</x>')))
    '{"x": {"$": "1"}}'
    >>> bf_str = BadgerFish(xml_fromstring=repr)    # Custom string parser
    '{"x": {"$": "\'1\'"}}'

``xml_fromstring`` can be any custom function that takes a string and returns a
value. In the example below, only the integer ``1`` is converted to an integer.
Everything else is retained as a float::

    >>> def convert_only_int(val):
    ...     return int(val) if val.isdigit() else val
    >>> bf_int = BadgerFish(xml_fromstring=convert_only_int)
    >>> dumps(bf_int.data(fromstring('<p><x>1</x><y>2.5</y><z>NaN</z></p>')))
    '{"p": {"x": {"$": 1}, "y": {"$": "2.5"}, "z": {"$": "NaN"}}}'


Conventions
-----------

To use a different conversion method, replace ``BadgerFish`` with one of the
other classes. Currently, these are supported::

    >>> from xmljson import abdera          # == xmljson.Abdera()
    >>> from xmljson import badgerfish      # == xmljson.BadgerFish()
    >>> from xmljson import cobra           # == xmljson.Cobra()
    >>> from xmljson import gdata           # == xmljson.GData()
    >>> from xmljson import parker          # == xmljson.Parker()
    >>> from xmljson import yahoo           # == xmljson.Yahoo()


Options
-------

Conventions may support additional options.

The `Parker`_ convention absorbs the root element by default.
``parker.data(preserve_root=True)`` preserves the root instance::

    >>> from xmljson import parker, Parker
    >>> from xml.etree.ElementTree import fromstring
    >>> from json import dumps
    >>> dumps(parker.data(fromstring('<x><a>1</a><b>2</b></x>')))
    '{"a": 1, "b": 2}'
    >>> dumps(parker.data(fromstring('<x><a>1</a><b>2</b></x>'), preserve_root=True))
    '{"x": {"a": 1, "b": 2}}'


Installation
------------

This is a pure-Python package built for Python 2.7+ and Python 3.0+. To set up::

    pip install xmljson


Simple CLI utility
------------------

After installation, you can benefit from using this package as simple CLI utility. By now only XML to JSON conversion supported. Example::

    $ python -m xmljson -h
    usage: xmljson [-h] [-o OUT_FILE]
                [-d {abdera,badgerfish,cobra,gdata,parker,xmldata,yahoo}]
                [in_file]

    positional arguments:
    in_file               defaults to stdin

    optional arguments:
    -h, --help            show this help message and exit
    -o OUT_FILE, --out_file OUT_FILE
                            defaults to stdout
    -d {abdera,badgerfish,...}, --dialect {...}
                            defaults to parker

    $ python -m xmljson -d parker tests/mydata.xml
    {
      "foo": "spam",
      "bar": 42
    }

This is a typical UNIX filter program: it reads file (or ``stdin``), processes it in some way (convert XML to JSON in this case), then prints it to ``stdout`` (or file). Example with pipe::

    $ some-xml-producer | python -m xmljson | some-json-processor

There is also ``pip``'s ``console_script`` entry-point, you can call this utility as ``xml2json``::

    $ xml2json -d abdera mydata.xml

Roadmap
-------

* Test cases for Unicode
* Support for namespaces and namespace prefixes
* Support XML comments
