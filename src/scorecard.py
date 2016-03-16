"""PMML Scorecard generator"""

from collections import namedtuple
import itertools
import os.path
import string
from lxml import etree
import tabulate

__version__ = "0.3"

__all__ = ["pmml_scorecard", "generate_scorecards"]

# Public API
def pmml_scorecard(json_scorecard, parameters=None):
    """Converts a JSON scorecard to a PMML scorecard

    *parameters* is an optional mapping for $-substitions in predicates
    """
    parsed_model = _json_to_internal(json_scorecard, parameters)
    return _internal_to_pmml(*parsed_model)

def characteristic_table(characteristics):
    """Print characteristic definitions in tabular form"""
    headings = "Criterion", "Partial Score", "Reason Code"
    data_rows = []
    for name, attributes in characteristics:
        data_rows.append(("===== " + name + " =====", "====", "===="))
        for reasonCode, partialScore, predicate in attributes:
            if predicate is None:
                full_predicate = name + " missing"
            else:
                try:
                    full_predicate = name + " " + predicate
                except TypeError:
                    predicate_parts = [name + " " + part for part in predicate]
                    full_predicate = " && ".join(predicate_parts)
            data_rows.append((full_predicate, partialScore, reasonCode))
    return tabulate.tabulate(data_rows, headings, tablefmt="psql")


def generate_scorecards(input_spec, output_dir):
    """Generates one or more PMML scorecards from parameterised input spec"""
    base_model_name = input_spec["model_name"]
    parameters = input_spec.get("param_grid")
    if parameters is None:
        param_grid = [None]
    else:
        degrees_of_freedom = []
        for var, options in sorted(parameters.items()):
            flattened = [(var, suffix, val) for suffix, val in options.items()]
            degrees_of_freedom.append(flattened)
        param_grid = itertools.product(*degrees_of_freedom)
    generated_scorecards = []
    for param_entry in param_grid:
        output_parts = [base_model_name]
        param_values = {}
        if param_entry is not None:
            for var, suffix, val in param_entry:
                output_parts.append(suffix)
                param_values[var] = val
        model_name = "_".join(output_parts)
        __, data_fields, characteristics = _json_to_internal(input_spec,
                                                             param_values)
        scorecard_xml = _internal_to_pmml(model_name,
                                          data_fields,
                                          characteristics)
        output_fname = os.path.join(output_dir, model_name + ".xml")
        with open(output_fname, "wb") as pmml_output:
            pmml_output.write(scorecard_xml)
        generated_scorecards.append((model_name, output_fname, characteristics))
    return generated_scorecards

# Implementation details

# Relevant PMML element details
DataField = namedtuple("DataField", "name dataType optype values")
Characteristic = namedtuple("Characteristic", "name attributes")
Attribute = namedtuple("Attribute", "reasonCode partialScore predicate")

# Comparison operator conversion
_cmpopmap = {
    "<":"lessThan",
    "<=":"lessOrEqual",
    "==":"equal",
    ">=":"greaterOrEqual",
    ">":"greaterThan",
}

def _read_predicate(predicate, params):
    """Reads a predicate from JSON, substituting fields as appropriate"""
    if predicate is None or "$" not in predicate:
        return predicate
    return string.Template(predicate).substitute(params)
    # TODO: It would be preferable to only create the template once per input,
    #       rather than per parameter grid entry. Using a helper function
    #       decorated with functools.lru_cache when on Python 3, for example.

def _json_to_internal(json_scorecard, params):
    """Converts a JSON scorecard description to the internal representation"""
    model_name = json_scorecard["model_name"]
    data_fields = [
        DataField(df["name"], df["dataType"], df["optype"], df.get("values"))
            for df in json_scorecard["data_fields"]
    ]
    characteristics = [
        Characteristic(c["name"],
                       [
                           Attribute(a["reasonCode"],
                                     str(a["partialScore"]),
                                     _read_predicate(a["predicate"], params))
                               for a in c["attributes"]
                       ]
                      )
            for c in json_scorecard["characteristics"]
    ]
    return model_name, data_fields, characteristics


def _internal_to_pmml(model_name, data_fields, characteristic_fields):
    """Converts an internal scorecard description to rendered PMML"""

    # Header
    root = etree.Element("PMML", version="4.2",
                         xmlns="http://www.dmg.org/PMML-4_2")
    header = etree.SubElement(root, "Header")

    # Data dictionary
    datadict = etree.SubElement(root, "DataDictionary")
    for name, dataType, optype, values in data_fields:
        field = etree.SubElement(datadict, "DataField", name=name,
                                 dataType=dataType, optype=optype)
        if values is not None:
            if optype not in ("categorical", "ordinal"):
                raise ValueError("Cannot specify values for {0}".format(optype))
            for value in values:
                etree.SubElement(field, "Value", value=value)

    # Scorecard
    scorecard = etree.SubElement(root, "Scorecard",
                                 modelName=model_name,
                                 functionName="regression",
                                 useReasonCodes="true",
                                 reasonCodeAlgorithm="pointsAbove",
                                 initialScore="0",
                                 baselineScore="1",
                                 baselineMethod="min")

    # Query fields
    schema = etree.SubElement(scorecard, "MiningSchema")
    for name, dataType, optype, values in data_fields:
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
    for name, attributes in characteristic_fields:
        characteristic = etree.SubElement(characteristics, "Characteristic",
                                          name = name + "Score",
                                          reasonCode = name + "RC")
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

def main():
    import sys
    import json
    # TODO: switch to a proper argument processing library (probably click)
    spec_file = sys.argv[1]
    output_dir = sys.argv[2]
    with open(spec_file) as sc_source:
        input_spec = json.load(sc_source)
    scorecard_names = generate_scorecards(input_spec, output_dir)
    for model_name, output_fname, characteristics in scorecard_names:
        print("Generated {0} -> {1}".format(model_name, output_fname))
        print(characteristic_table(characteristics))

if __name__ == "__main__":
    main()
