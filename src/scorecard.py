from collections import namedtuple
from lxml import etree

__all__ = ["SchemaField", "Characteristic", "Attribute", "pmml_scorecard"]

# Relevant PMML element details
DataField = namedtuple("DataField", "name dataType optype")
Characteristic = namedtuple("Characteristic", "name baselineScore attributes")
Attribute = namedtuple("Attribute", "reasonCode partialScore predicate")

# Comparison operator conversion
_cmpopmap = {
    "<":"lessThan",
    "<=":"lessOrEqual",
    "==":"equal",
    ">=":"greaterOrEqual",
    ">":"greaterThan",
}

# Creating scorecards
def pmml_scorecard(model_name, data_fields, characteristic_fields):
    """Returns rendered PMML scorecard for given scorecard definition"""

    # Header
    root = etree.Element("PMML", version="4.2",
                         xmlns="http://www.dmg.org/PMML-4_2")
    header = etree.SubElement(root, "Header")

    # Data dictionary
    datadict = etree.SubElement(root, "DataDictionary")
    for field in data_fields:
        etree.SubElement(datadict, "DataField", **field._asdict())

    # Scorecard
    scorecard = etree.SubElement(root, "Scorecard",
                                 modelName=model_name,
                                 functionName="regression",
                                 useReasonCodes="true",
                                 reasonCodeAlgorithm="pointsAbove",
                                 initialScore="0",
                                 baselineScore="0",
                                 baselineMethod="min")

    # Query fields
    schema = etree.SubElement(scorecard, "MiningSchema")
    for name, dataType, optype in data_fields:
        element = etree.SubElement(schema, "MiningField", name=name)

    # Output fields
    output = etree.SubElement(scorecard, "Output")
    etree.SubElement(output, "OutputField",
                     name="RiskScore",
                     feature="predictedValue",
                     dataType="double",
                     optype="continuous")
    for i in range(1, 4):
        etree.SubElement(output, "OutputField",
                         name="ReasonCode" + str(i),
                         rank=str(i),
                         feature="reasonCode",
                         dataType="string",
                         optype="categorical")

    # Characteristic scoring
    characteristics = etree.SubElement(scorecard, "Characteristics")
    for name, baselineScore, attributes in characteristic_fields:
        characteristic = etree.SubElement(characteristics, "Characteristic",
                                          name = name + "Score",
                                          reasonCode = name + "RC",
                                          baselineScore = baselineScore)
        for attribute in attributes:
            _render_pmml_attribute(characteristic, name, attribute)

    # Return rendered schema
    return etree.tostring(root, pretty_print=True, xml_declaration=True)

def _render_pmml_attribute(characteristic, name, attribute_details):
    """Render PMML Attribute as part of given Characteristic"""
    reasonCode, partialScore, predicate = attribute_details
    attribute = etree.SubElement(characteristic, "Attribute",
                                 reasonCode = reasonCode,
                                 partialScore = partialScore)
    # Predicate of None -> isMissing
    if predicate is None:
        etree.SubElement(attribute, "SimplePredicate",
                         field=name, operator="isMissing")
        return
    # String -> simple comparison predicate
    try:
        rule = predicate.strip()
    except AttributeError:
        pass
    else:
        cmpop, value = rule.split()
        operator = _cmpopmap[cmpop]
        etree.SubElement(attribute, "SimplePredicate",
                         field=name, operator=operator, value=value)
        return
    # Otherwise -> list of simple predicates anded together
    and_group = etree.SubElement(attribute, "CompoundPredicate",
                                 booleanOperator="and")
    for rule in predicate:
        cmpop, value = rule.strip().split()
        operator = _cmpopmap[cmpop]
        etree.SubElement(and_group, "SimplePredicate",
                         field=name, operator=operator, value=value)

if __name__ == "__main__":
    # Print example scorecard
    import sys
    import json
    with open(sys.argv[1]) as sc_source:
        sc_details = json.load(sc_source)

    model_name = sc_details["model_name"]
    data_fields = [
        DataField(df["name"], df["dataType"], df["optype"])
            for df in sc_details["data_fields"]
    ]
    characteristics = [
        Characteristic(c["name"],
                       str(c["baselineScore"]),
                       [
                           Attribute(a["reasonCode"],
                                     str(a["partialScore"]),
                                     a["predicate"])
                               for a in c["attributes"]
                       ]
                      )
            for c in sc_details["characteristics"]
    ]

    print(pmml_scorecard(model_name, data_fields, characteristics))
