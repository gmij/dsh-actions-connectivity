"""Validate DSH output as data and write only fixed artifact filenames."""
import json
import re


def write_bundle(raw, destination):
    raw = raw.strip()
    if raw.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', raw, re.S)
        if not match:
            raise ValueError('Expected one JSON object')
        raw = match.group(1)
    data = json.loads(raw)
    required = {'needs_prototype', 'decision_reason', 'requirements_markdown', 'design_markdown', 'prototype_html'}
    if not isinstance(data, dict) or set(data) != required or type(data['needs_prototype']) is not bool:
        raise ValueError('Invalid prototype contract')
    for key in required - {'needs_prototype'}:
        if not isinstance(data[key], str) or len(data[key]) > 250000:
            raise ValueError('Invalid text field')
    if not data['decision_reason'].strip() or not data['requirements_markdown'].strip():
        raise ValueError('Decision and requirements are required')
    html = data['prototype_html']
    if data['needs_prototype']:
        if len(html) < 500 or not re.search(r'<!doctype html', html, re.I) or '<html' not in html.lower() or not re.search(r'<head\b[^>]*>', html, re.I) or not data['design_markdown'].strip():
            raise ValueError('Expected a complete HTML prototype and design notes')
        if not re.search(r'name=[\"\']viewport[\"\']', html, re.I):
            raise ValueError('Responsive viewport is required')
        if re.search(r'<(?:script|iframe|link)\b[^>]*(?:src|href)\s*=\s*[\"\'](?:https?:)?//', html, re.I):
            raise ValueError('External scripts, stylesheets and frames are unsupported')
    elif html.strip():
        raise ValueError('A no-prototype decision must not include HTML')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'decision.json').write_text(json.dumps({k: data[k] for k in ['needs_prototype', 'decision_reason']}, ensure_ascii=False, indent=2))
    (destination / 'requirements.md').write_text(data['requirements_markdown'])
    (destination / 'design.md').write_text(data['design_markdown'])
    if data['needs_prototype']:
        # Interactions run only in the viewer's browser; block outbound requests.
        csp = '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; script-src &#39;unsafe-inline&#39;; style-src &#39;unsafe-inline&#39;; img-src data:; connect-src &#39;none&#39;; form-action &#39;none&#39;; frame-src &#39;none&#39;; base-uri &#39;none&#39;; object-src &#39;none&#39;">'
        html = re.sub(r'(<head\b[^>]*>)', lambda match: match.group(1) + csp, html, count=1, flags=re.I)
        (destination / 'index.html').write_text(html)
    elif (destination / 'index.html').exists():
        (destination / 'index.html').unlink()
    (destination / 'README.md').write_text('解压后用浏览器打开 index.html。此为交互原型，数据为演示数据，不连接真实业务。若 decision.json 中 needs_prototype 为 false，则不生成界面。\n')
    status = '需要原型；已生成交互 HTML' if data['needs_prototype'] else '本任务不需要原型'
    return f"### 原型判断\n{status}。\n\n{data['decision_reason']}\n\n### 需求分析\n{data['requirements_markdown']}\n\n### 设计说明\n{data['design_markdown']}"
