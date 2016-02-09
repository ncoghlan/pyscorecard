from collections import namedtuple
from lxml import etree

__all__ = ["SchemaField", "Characteristic", "Attribute", "pmml_scorecard"]

# Relevant PMML element details
DataField = namedtuple("DataField", "name dataType optype")
MiningField = namedtuple("MiningField", "name usageType")
OutputField = namedtuple("OutputField", "name feature dataType optype")
Characteristic = namedtuple("Characteristic", "name baselineScore attributes")
Attribute = namedtuple("Attribute", "reasonCode partialScore predicate")

# Merged input type for describing data and mining fields
SchemaField = namedtuple("SchemaField", "name dataType optype usageType")

# Constants and lookup tables
_output_fields = [
    OutputField("RiskScore", "predictedValue", "double", "continuous"),
    OutputField("ReasonCode1", "reasonCode", "string", "categorical"),
    OutputField("ReasonCode2", "reasonCode", "string", "categorical"),
    OutputField("ReasonCode3", "reasonCode", "string", "categorical"),
]

_cmpopmap = {
    "<":"lessThan",
    "<=":"lessOrEqual",
    "==":"equal",
    ">=":"greaterOrEqual",
    ">":"greaterThan",
}

# Creating scorecards
def pmml_scorecard(model_name, schema_fields, characteristic_fields):
    """Returns rendered PMML scorecard for given scorecard definition"""
    data_fields = []
    mining_fields = []
    for name, dataType, optype, usageType in schema_fields:
        data_fields.append(DataField(name=name, dataType=dataType, optype=optype))
        mining_fields.append(MiningField(name=name, usageType=usageType))

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
    for name, usageType in mining_fields:
        element = etree.SubElement(schema, "MiningField", name=name)
        if usageType is not None:
            element.set("usageType", usageType)

    # Output fields
    output = etree.SubElement(scorecard, "Output")
    for field in _output_fields:
        etree.SubElement(output, "OutputField", **field._asdict())

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
        return

if __name__ == "__main__":
    # Print example scorecard
    schema_fields = [
        SchemaField("role", "string", "categorical", None),
        SchemaField("age", "integer", "continuous", None),
        SchemaField("wage", "double", "continuous", None),
        SchemaField("calculatedScore", "double", "continuous", "predicted"),
    ]

    characteristic_fields = [
        Characteristic("role", "0",
                    [
                        Attribute("RoleMissing", "20", None),
                        Attribute("RoleMRKT", "10", "== 'marketing'"),
                        Attribute("RoleENGR", "5", "== 'engineering'"),
                        Attribute("RoleBSNS", "10", "== 'business'"),
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
    print(pmml_scorecard("ExampleModel", schema_fields, characteristic_fields))