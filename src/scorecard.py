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
    data_fields = [
        DataField("role", "string", "categorical"),
        DataField("age", "integer", "continuous"),
        DataField("wage", "double", "continuous"),
    ]

    characteristics = [
        Characteristic("role", "0",
                    [
                        Attribute("RoleMissing", "20", None),
                        Attribute("RoleMRKT", "10", "== marketing"),
                        Attribute("RoleENGR", "5", "== engineering"),
                        Attribute("RoleBSNS", "10", "== business"),
                    ]
                    ),
        Characteristic("age", "0",
                    [
                        Attribute("AgeMissing", "20", None),
                        Attribute("AgeChild", "15", "<= 18"),
                        Attribute("AgeYoungAdult", "25", ["> 18", "<= 29"]),
                        Attribute("AgeAdult", "5", ["> 29", "<= 39"]),
                        Attribute("AgeOlderAdult", "0", "> 39"),
                    ]
                    ),
        Characteristic("wage", "0",
                    [
                        Attribute("WageMissing", "20", None),
                        Attribute("WageLow", "25", "<= 1000"),
                        Attribute("WageMedium", "10", ["> 1000", "<= 2500"]),
                        Attribute("WageHigh", "0", "> 2500"),
                    ]
                    ),
    ]
    print(pmml_scorecard("ExampleModel", data_fields, characteristics))