# pyscorecard
Python client for submitting PMML ScoreCard models and queries against them to OpenScoring

PMML ScoreCards: http://dmg.org/pmml/v4-2-1/Scorecard.html for additional background

OpenScoring REST API: https://github.com/jpmml/openscoring
Demo instance: http://openscoring-ncoghlan.rhcloud.com/openscoring/
Demo git repo: https://github.com/ncoghlan/openscoring-openshift

## PMML ScoreCard generation from JSON input

scorecard.pmml_scorecard generates PMML scorecard definitions from a
JSON-compatible input mapping.

See examples/risk_example.json (input) and examples/risk_example.xml (output)

All ScoreCards produce a single predicted risk score and up to 3 reason codes:

* `RiskScore`
* `ReasonCode1`
* `ReasonCode2`
* `ReasonCode3`

Generated ScoreCards are also currently all hardcoded to use the "pointsAbove"
reason code algorithm, the "min" baseline score algorithm, and `0` as the
initial and baseline score for the overall scorecard evaluation.

The input format is a JSON mapping with the following fields:

* `model_name`: name of the model
* `data_fields`: sequence of field definitions for the DataDictionary and
  MiningSchema sections in the generated PMML Scorecard

  * `name`: used in both the DataField entry and the MiningField entry
  * `dataType`: used in the DataField entry
  * `optype`: used in the DataField entry to define handling of comparisons

* `characteristics`: sequence of definitions for the Characteristic section in
  the generated PMML Scorecard

  * `name`: data field used by this characteristic. Also used to derive the
    characteristic name as `name + "Score"` and the overall characteristic
    reason code as `name + "RC"`
  * `baselineScore`: baseline contribution to the risk score for this
    characteristic
  * `attributes`: sequence of attribute definitions used by the characteristic

    * `reasonCode`: specific reason code when this criterion is met
    * `partialScore`: contribution to the risk score when this criterion is met
    * `predicate`: predicate defining this criterion (see below for details)

Predicates can be defined as either a single string, or as a sequence of such
strings. Each string predicate is of the form "OP value", with the data field
named in the characteristic definition being the implied left hand side of
the operation. Predicate sequences are implicitly and'ed together to define
the overall criterion to be met for that attribute.

Permitted operations are `==` for data fields with the categorical optype, and
`==`, `<`, `<=`, `>=`, and `>` for data fields with the continuous optype
(while other optypes are defined in PMML, they are not yet supported
in pyscorecard).

