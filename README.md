# pyscorecard
Python client for submitting PMML ScoreCard models and queries against them to OpenScoring

PMML ScoreCards: http://dmg.org/pmml/v4-2-1/Scorecard.html for additional background

OpenScoring REST API: https://github.com/jpmml/openscoring
Demo instance: http://openscoring-ncoghlan.rhcloud.com/openscoring/
Demo git repo: https://github.com/ncoghlan/openscoring-openshift

## PMML ScoreCard generation from JSON input

Command line invocation:

    pyscorecard input_spec.json pmml_output_dir

Output PMML file names are generated based on a combination of "model_name"
and "param_grid" entries as described below.

In the Python API, `scorecard.pmml_scorecard` generates PMML scorecard
definitions from a JSON-compatible input mapping.

See examples/risk_example.json (input) and examples/risk_example.xml (output)

All ScoreCards produce a single predicted risk score and up to 3 reason codes:

* `RiskScore`
* `ReasonCode1`
* `ReasonCode2`
* `ReasonCode3`

Generated ScoreCards are also currently all hardcoded to use the "pointsAbove"
reason code algorithm, the "min" baseline score algorithm, `0` as the
initial score for the overall scorecard evaluation and `1` as the baseline
score for each individual characteristic (this ensures that characteristics
achieving a partial score of `0` are never reported as reason codes for the
overall risk scoring).

The input format is a JSON mapping with the following fields:

* `model_name`: name of the model (also used as output filename prefix)
* `param_grid`: parameter definitions for use in characteristic predicates

  * key is the variable name that can be substituted into predicates
  * value is a mapping of output filename suffixes to substition values
  * when multiple grid parameters are defined, keys are lexically sorted
    when determining the combined output filename

* `data_fields`: sequence of field definitions for the DataDictionary and
  MiningSchema sections in the generated PMML Scorecard

  * `name`: used in both the DataField entry and the MiningField entry
  * `dataType`: used in the DataField entry
  * `optype`: used in the DataField entry to define handling of comparisons
  * `values`: permitted values for categorical and ordinal fields

* `characteristics`: sequence of definitions for the Characteristic section in
  the generated PMML Scorecard

  * `name`: data field used by this characteristic. Also used to derive the
    characteristic name as `name + "Score"` and the overall characteristic
    reason code as `name + "RC"`
  * `attributes`: sequence of attribute definitions used by the characteristic

    * `reasonCode`: specific reason code when this criterion is met
    * `partialScore`: contribution to the risk score when this criterion is met
    * `predicate`: predicate defining this criterion (see below for details)

Predicates can be defined as either a single string, or as a sequence of such
strings. Each string predicate is of the form "OP value", with the data field
named in the characteristic definition being the implied left hand side of
the operation. Predicate sequences are implicitly and'ed together to define
the overall criterion to be met for that attribute. Predicate values may
start with `$` to indicate a grid parameter - these will be substituted with
the appropriate value for the scorecard currently being generated.

Permitted operations are `==` for data fields with the `categorical` optype, and
`==`, `<`, `<=`, `>=`, and `>` for data fields with the `ordinal` or
`continuous` optype.

