import copy
import unittest
from design_delivery import validate_delivery, schema_check

OBJ=lambda p: {"type":"object","properties":{p:{"type":"string"}},"required":[p],"additionalProperties":False}
def fixture():
    channel={"id":"IPC-01","module_id":"MOD-01","task_id":"TASK-01","transport":"vscode-webview","command":"chat.send",
      "request":OBJ("message"),"request_example":{"message":"hello"},
      "response":OBJ("reply"),"response_example":{"reply":"hi"},
      "error":OBJ("code"),"error_example":{"code":"FAILED"},
      "bindings":[{"page_id":"UI-01","action":"send message","request_mapping":[{"source":"chatInput","target":"message"}],
      "response_mapping":[{"source":"reply","target":"chatOutput"}],"loading_behavior":"loading","error_behavior":"show error","success_behavior":"show reply"}]}
    return {"experience":{"interaction_mode":"web"},"modules":[{"id":"MOD-01",
      "tasks":[{"id":"TASK-01","layer":"backend"}],"frontend":{"pages":[{"id":"UI-01"}]}}],
      "delivery":{"apis":[],"bindings":[],"channels":[channel],"prototype_html":"<!doctype html><html><head></head><body>"+"x"*550+"</body></html>"}}

class NullableObjectSchemaTests(unittest.TestCase):
    def test_nullable_object_with_null_example(self):
        schema = {'type': ['object', 'null'], 'properties': {
            'code': {'type': 'string'}},
            'required': ['code'], 'additionalProperties': False}
        schema_check(schema, None, 'IPC-07.response.error')
        schema_check(schema, {'code': 'DISCONNECTED'}, 'IPC-07.response.error')

    def test_null_rejected_when_not_nullable(self):
        schema = {'type': 'object', 'properties': {
            'code': {'type': 'string'}},
            'required': ['code'], 'additionalProperties': False}
        with self.assertRaises(ValueError):
            schema_check(schema, None, 'IPC-07.response.error')

    def test_invalid_non_null_object_still_rejected(self):
        schema = {'type': ['object', 'null'], 'properties': {
            'code': {'type': 'string'}},
            'required': ['code'], 'additionalProperties': False}
        with self.assertRaises(ValueError):
            schema_check(schema, {}, 'IPC-07.response.error')


class TypedChannelTests(unittest.TestCase):
    def test_non_http_ipc_contract_passes(self):
        validate_delivery(fixture(), required=True)
    def test_missing_channels_rejected(self):
        x=fixture();x["delivery"]["channels"]=[]
        with self.assertRaisesRegex(ValueError,"at least one HTTP API"):
            validate_delivery(x, required=True)
    def test_missing_page_binding_rejected(self):
        x=fixture();x["delivery"]["channels"][0]["bindings"]=[]
        with self.assertRaises(ValueError): validate_delivery(x,required=True)
    def test_invalid_response_field_rejected(self):
        x=fixture();x["delivery"]["channels"][0]["bindings"][0]["response_mapping"][0]["source"]="unknown"
        with self.assertRaises(ValueError): validate_delivery(x,required=True)
    def test_http_not_silently_accepted_without_binding(self):
        x=fixture();x["delivery"]["apis"]=[{}]
        with self.assertRaisesRegex(ValueError,"HTTP APIs require"):
            validate_delivery(x,required=True)

if __name__=="__main__": unittest.main()
