"""Offline checks for translations and unchanged control payloads."""
import ast
import asyncio
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / 'custom_components/hargassner'

def shape(value):
    if isinstance(value, dict):
        return {key: shape(val) for key, val in value.items()}
    return type(value).__name__

class TranslationTests(unittest.TestCase):
    def test_languages_have_identical_keys_and_placeholders(self):
        source = json.loads((COMP / 'strings.json').read_text(encoding='utf-8'))
        def placeholders(data, prefix=''):
            result = {}
            for key, val in data.items():
                if isinstance(val, dict):
                    result.update(placeholders(val, prefix+key+'.'))
                elif isinstance(val, str):
                    result[prefix+key] = set(re.findall(r'\{([^}]+)\}', val))
            return result
        for lang in ('en', 'de', 'fr'):
            target = json.loads((COMP / f'translations/{lang}.json').read_text(encoding='utf-8'))
            self.assertEqual(shape(source), shape(target), lang)
            self.assertEqual(placeholders(source), placeholders(target), lang)

    def test_all_entity_description_keys_are_translated(self):
        data=json.loads((COMP/'translations/de.json').read_text(encoding='utf-8'))
        for platform in ('sensor','number','switch'):
            tree=ast.parse((COMP/f'{platform}.py').read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and getattr(node.func,'id','').endswith('Description'):
                    kw={x.arg:x.value for x in node.keywords}
                    if isinstance(kw.get('key'),ast.Constant):
                        key=kw['key'].value
                        self.assertEqual(kw['translation_key'].value,key)
                        self.assertIn(key,data['entity'][platform])
                        self.assertNotIn('name',kw)

    def test_control_methods_and_unique_ids_unchanged(self):
        for platform in ('sensor','number','select','switch','climate','entity_base'):
            path=f'custom_components/hargassner/{platform}.py'
            before=ast.parse(subprocess.check_output(['git','show','b08bdfa2de3effa7d617f20f7c8078d9d34a6576:'+path],cwd=ROOT).decode())
            after=ast.parse((ROOT/path).read_text(encoding='utf-8'))
            def important(tree):
                return [ast.dump(n,include_attributes=False) for n in ast.walk(tree)
                        if (isinstance(n,ast.AsyncFunctionDef) and n.name.startswith(('async_set_','async_turn_','async_select_')))
                        or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='_attr_unique_id' for t in n.targets))]
            self.assertEqual(important(before),important(after),platform)

    def test_select_translation_retains_api_payloads(self):
        tree=ast.parse((COMP/'select.py').read_text(encoding='utf-8'))
        kept=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')],level=0)]
        kept += [n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('MODE_LABELS','POOL_LABELS') for t in n.targets)]
        kept += [n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='HargassnerSelectEntity']
        class Base:
            def __init__(self,coordinator,*args): self.coordinator=coordinator
            def _get_parameter(self): return self.param
            def _get_resource(self): return '/test/resource'
        class Select: pass
        class Coordinator:
            async def async_patch_value(self,resource,value): self.sent=(resource,value)
        ns={'HargassnerEntity':Base,'SelectEntity':Select}
        exec(compile(ast.fix_missing_locations(ast.Module(body=kept,type_ignores=[])),'select-test','exec'),ns)
        for group,param_key in [('MODE_LABELS','mode'),('POOL_LABELS','pool_heating')]:
            coordinator=Coordinator()
            entity=ns['HargassnerSelectEntity'](coordinator,'hk1',param_key,'EG','unused',ns[group])
            for api_value,label in ns[group].items():
                entity.param={'options':list(ns[group]),'value':api_value}
                self.assertEqual(entity.current_option,label)
                self.assertIn(label,entity.options)
                asyncio.run(entity.async_select_option(label))
                self.assertEqual(coordinator.sent,('/test/resource',api_value))
            self.assertEqual(entity._attr_translation_placeholders,{'widget_name':'EG'})

    def test_python_syntax(self):
        for path in COMP.glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

if __name__=='__main__': unittest.main()

