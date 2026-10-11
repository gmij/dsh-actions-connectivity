import copy
import json
import tempfile
from pathlib import Path
import unittest
from design_delivery import validate_delivery


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def delivery_example():
    empty=obj({}); text={'type':'string','minLength':1}; html='<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px system-ui;background:#f6f7f6;margin:0;color:#26352f}main{max-width:720px;margin:40px auto;padding:24px}button{padding:10px;border:1px solid #abc;border-radius:8px;background:#e8f0ed;color:#234c3c;cursor:pointer}p{line-height:1.6}h1{font-size:24px}</style></head><body><main><h1>同步管理</h1><p>模拟数据交互原型</p><button id="sync">开始同步</button><p id="status">就绪</p><script>document.querySelector("#sync").onclick=()=>document.querySelector("#status").textContent="成功2条，失败1条";</script></main></body></html>'
    return {'apis':[{'id':'API-01','module_id':'MOD-01','task_id':'TASK-01','method':'POST','path':'/api/sync','title':'启动同步','auth':'仅内网同源演示','request':{'path':empty,'query':empty,'body':obj({'supplierId':text})},'request_example':{'path':{},'query':{},'body':{'supplierId':'gutendex-sim'}},'responses':[{'status':200,'description':'同步结果','schema':obj({'successCount':{'type':'integer','minimum':0},'failedCount':{'type':'integer','minimum':0}}),'example':{'successCount':2,'failedCount':1}},{'status':502,'description':'供应商错误','schema':obj({'code':text,'message':text}),'example':{'code':'UPSTREAM_UNAVAILABLE','message':'请重试'}}]}],'bindings':[{'id':'BIND-01','page_id':'UI-01','action':'同步按钮点击','api_id':'API-01','response_status':200,'request_mapping':[{'target':'body.supplierId','source':'SupplierSelect.value'}],'response_mapping':[{'source':'successCount','target':'Status.successCount'},{'source':'failedCount','target':'Status.failedCount'}],'loading_behavior':'禁用按钮','error_behavior':'显示message并允许重试','success_behavior':'显示计数'}],'prototype_html':html}


class DeliveryTests(unittest.TestCase):
    def data(self):
        from test_mvp_design import example2
        return example2()
    def test_reject_missing_response_field_and_unknown_bindings(self):
        d=self.data();d['delivery']['apis'][0]['responses'][0]['example'].pop('failedCount')
        with self.assertRaises(ValueError):validate_delivery(d,True)
        d=self.data();d['delivery']['bindings'][0]['response_mapping'][0]['source']='missing'
        with self.assertRaises(ValueError):validate_delivery(d,True)
    def test_request_required_mapping_and_backend_ownership(self):
        d=self.data();d['delivery']['bindings'][0]['request_mapping']=[]
        with self.assertRaises(ValueError):validate_delivery(d,True)
        d=self.data();d['delivery']['apis'][0]['task_id']='TASK-02'
        with self.assertRaises(ValueError):validate_delivery(d,True)
    def test_new_web_delivery_cannot_omit_contracts_or_prototype(self):
        d=self.data();d.pop('delivery')
        with self.assertRaises(ValueError):validate_delivery(d,True)
        d=self.data();d['delivery']['prototype_html']=''
        with self.assertRaises(ValueError):validate_delivery(d,True)
    def test_renders_distinct_interfaces_and_prototype_from_same_design(self):
        from design_output import write_bundle
        with tempfile.TemporaryDirectory() as f:
            dest=Path(f)/'design';write_bundle(json.dumps(self.data()),dest,'detailed',True)
            s=(dest/'apis/API-01.md').read_text();self.assertIn('## 响应 200',s);self.assertIn('## 响应 502',s);self.assertIn('supplierId',s)
            self.assertIn('body.supplierId',(dest/'frontend-bindings.md').read_text());self.assertTrue((dest.parent/'prototype/index.html').exists())

class WikiDeliveryTests(unittest.TestCase):
    def test_verified_preview_images_and_api_navigation(self):
        from design_wiki import assemble
        from test_mvp_design import example2
        preview='https://example.github.io/demo/previews/issue-17/runs/100/'
        result,state=assemble({}, {}, 'gmij/dsh-actions-connectivity',17,100,'detailed',json.dumps(example2()),preview)
        self.assertIn('![桌面界面]('+preview+'desktop.png)',result['Issue-17-Detailed-UI.md'])
        self.assertIn('Issue-17-Detailed-API-01',result['Issue-17-Detailed-APIs.md'])
        self.assertIn('Issue-17-Detailed-APIs',result['_Sidebar.md'])
        self.assertIn('body.supplierId',result['Issue-17-Detailed-Bindings.md'])

class ScreenshotStorageTests(unittest.TestCase):
    def test_existing_png_survives_next_preview_assembly(self):
        from prototype_pages import assemble
        from prototype_output import CSP
        html=delivery_example()['prototype_html'].replace('<head>','<head>'+CSP)
        old={'previews/issue-14/runs/99/desktop.png':b'\x89PNG\r\n\x1a\n'}
        result,latest,version=assemble(old,17,100,html)
        self.assertEqual(result['previews/issue-14/runs/99/desktop.png'],old['previews/issue-14/runs/99/desktop.png'])
