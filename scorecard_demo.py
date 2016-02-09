#!/usr/bin/env python

# Currently using raw requests, but could potentially switch to using
# the AGPLv3 https://github.com/jpmml/openscoring-python
# convenience wrapper instead
import requests
import json

# For the OpenShift demo instance, models are uploaded via the
# git repo, rather than via
base_url = "http://openscoring-ncoghlan.rhcloud.com/openscoring/model/"

# Query for a score with explanatory reason codes

# Example uses the following query schema
# age: double
# wage: integer
# role: [ "engineering", "marketing", "business" ]
reason_code_url = base_url + "risk_example"

def reason_code_query(data):
    query_url = reason_code_url
    body = {
        "id" : "reason-code-demo-query",
        "arguments" : data
    }
    response = requests.post(reason_code_url, json=body)
    response.raise_for_status()
    result = response.json()["result"]
    return (result["RiskScore"], result["ReasonCode1"],
            result["ReasonCode2"], result["ReasonCode3"])

reason_code_examples = [
{},
{
  "age": 37,
  "role": "engineering",
  "wage": 1500,
},
{
  "age": 21,
  "role": "marketing",
  "wage": 500,
},
]

for example in reason_code_examples:
    print("Query: {}".format(example))
    print("Result: {}\n".format(reason_code_query(example)))
