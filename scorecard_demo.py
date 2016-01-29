#!/usr/bin/env python

# Currently using raw requests, but could potentially switch to using
# the AGPLv3 https://github.com/jpmml/openscoring-python
# convenience wrapper instead
import requests
import json

# For the OpenShift demo instance, models are uploaded via the
# git repo, rather than via
base_url = "http://openscoring-ncoghlan.rhcloud.com/openscoring/model/"

# Query for a score without any explanatory codes

# Example uses a Drools test case with the following query schema
# age: double
# occupation: [ "SKYDIVER", "ASTRONAUT", "PROGRAMMER", "TEACHER", "INSTRUCTOR" ]
# residenceState: [ "AP", "KN", "TN" ]
# validLicense: boolean
score_only_url = base_url + "drools_pmml_test_scorecard"

def score_only_query(data):
    query_url = score_only_url
    body = {
        "id" : "score-only-demo-query",
        "arguments" : data
    }
    response = requests.post(score_only_url,
                             data = json.dumps(body), json = None,
                             headers = {"content-type" : "application/json"})
    response.raise_for_status()
    return response.json()

score_only_example = {
  "age": 37,
  "occupation": "PROGRAMMER",
  "residenceState": "TN",
  "validLicense": True,
}

# print(score_only_query(score_only_example))

# Query for a score with explanatory reason codes

# Example uses a Drools test case with the following query schema
# age: double
# occupation: [ "SKYDIVER", "ASTRONAUT", "PROGRAMMER", "TEACHER", "INSTRUCTOR" ]
# residenceState: [ "AP", "KN", "TN" ]
# validLicense: boolean
reason_code_url = base_url + "drools_pmml_test_scorecardOut"

def reason_code_query(data):
    query_url = reason_code_url
    body = {
        "id" : "reason-code-demo-query",
        "arguments" : data
    }
    response = requests.post(reason_code_url,
                             data = json.dumps(body), json = None,
                             headers = {"content-type" : "application/json"})
    response.raise_for_status()
    return response.json()

reason_code_examples = [
{
  "age": 37,
  "cage": "engineering",
  "wage": 1500,
},
{
  "age": 21,
  "cage": "marketing",
  "wage": 500,
},
]

for example in reason_code_examples:
    print(reason_code_query(example))
