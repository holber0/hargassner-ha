"""Control tests with mocked coordinator; never contact a real boiler."""
import ast
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

COMP=Path(__file__).resolve().parents[1]/'custom_components/hargassner'
spec=importlib.util.spec_from_file_location('caps',COMP/'capabilities.py');caps=importlib.util.module_from_spec(spec);spec.loader.exec_module(caps)
class HAError(Exception):pass
class Base:
    def __init__(self,coordinator,key,param,suffix):self.coordinator=coordinator;self._widget_key=key;self._param_key=param
    def _get_widget(self):return self.coordinator.data.get(self._widget_key)
    def _get_parameter(self):return self._get_widget().get('parameters',{}).get(self._param_key)
    def _get_value(self):return self._get_widget().get('values',{}).get(self._param_key)
class Entity:pass

def load(filename):
    tree=ast.parse((COMP/filename).read_text(encoding='utf-8-sig'))
    tree.body=[x for x in tree.body if not isinstance(x,(ast.Import,ast.ImportFrom))]
    ns={'HargassnerEntity':Base,'ButtonEntity':Entity,'SelectEntity':Entity,'SwitchEntity':Entity,'BinarySensorEntity':Entity,'HomeAssistantError':HAError,'DOMAIN':'hargassner'}
    for key in ('enabled_resource','cloud_ready','allowed_programs','active_bool'):ns[key]=getattr(caps,key)
    exec(compile(tree,filename,'exec'),ns);return ns

class Coordinator:
    def __init__(self):
        self.last_update_success=True;self.sent=[];self.result=True;self.refresh_hook=None
        self.data={'_online':True,'heater':{'widget_type':'HEATER','widget_name':'Kessel','values':{'activated':0},'parameters':{'program':{'value':'PROGRAM_OFF','options':['PROGRAM_OFF','PROGRAM_AUTOMATIC','PROGRAM_MANUAL'],'resource':'/api/test/program'},'activated':{'resource':'/api/test/activated'}},'actions':{'start_heating':{'resource':'/api/test/start'},'stop_heating':{'resource':'/api/test/stop'},'start_ignition':{'resource':'/api/test/ignite'}}},'buffer':{'widget_type':'BUFFER','widget_name':'Puffer','values':{},'actions':{'force_charging':{'resource':'/api/test/charge'}}}}
    async def async_request_refresh(self):
        if self.refresh_hook:self.refresh_hook()
    async def async_patch_value(self,resource,value):self.sent.append(('PATCH',resource,value));return self.result
    async def async_post_action(self,resource):self.sent.append(('POST',resource));return self.result

class ControlTests(unittest.IsolatedAsyncioTestCase):
    def test_resources_reject_disabled_and_foreign_hosts(self):
        for item in [None,{}, {'resource':'https://evil.example/action'}, {'resource':'//evil.example/action'}, {'resource':'/api/action','disabled':True},{'resource':'/api/action','disabled':1},{'resource':'/api/action','read_only':True}]:self.assertIsNone(caps.enabled_resource(item))
        self.assertEqual(caps.enabled_resource({'resource':'/api/action','disabled':0}),'/api/action')

    async def test_setup_never_writes_and_only_advertised_actions(self):
        c=Coordinator();entities=[];hass=SimpleNamespace(data={'hargassner':{'entry':c}})
        await load('button.py')['async_setup_entry'](hass,SimpleNamespace(entry_id='entry'),entities.extend)
        self.assertEqual(len(entities),4);self.assertEqual(c.sent,[])
        del c.data['heater']['actions']['stop_heating'];entities=[]
        await load('button.py')['async_setup_entry'](hass,SimpleNamespace(entry_id='entry'),entities.extend)
        self.assertEqual(len(entities),3)

    async def test_buffer_charge_and_stop_use_exact_resources(self):
        c=Coordinator();cls=load('button.py')['HargassnerAction']
        for key,action in [('buffer','force_charging'),('heater','stop_heating')]:await cls(c,key,action,'Test').async_press()
        self.assertEqual(c.sent,[('POST','/api/test/charge'),('POST','/api/test/stop')])

    async def test_action_rechecks_disabled_after_refresh(self):
        c=Coordinator();obj=load('button.py')['HargassnerAction'](c,'heater','start_heating','Kessel')
        c.refresh_hook=lambda:c.data['heater']['actions']['start_heating'].update(disabled=True)
        with self.assertRaises(HAError):await obj.async_press()
        self.assertEqual(c.sent,[]);self.assertFalse(obj._busy)

    async def test_offline_blocks_controls(self):
        c=Coordinator();c.data['_online']=False
        obj=load('button.py')['HargassnerAction'](c,'heater','start_heating','Kessel')
        self.assertFalse(obj.available)
        with self.assertRaises(HAError):await obj.async_press()
        self.assertEqual(c.sent,[])

    async def test_api_failure_is_visible(self):
        c=Coordinator();c.result=False
        with self.assertRaises(HAError):await load('button.py')['HargassnerAction'](c,'heater','start_heating','Kessel').async_press()

    async def test_program_allowlist_and_payload(self):
        c=Coordinator();obj=load('boiler_control.py')['BoilerProgram'](c,'heater','Kessel')
        self.assertEqual(obj.options,['PROGRAM_OFF','PROGRAM_AUTOMATIC'])
        with self.assertRaises(HAError):await obj.async_select_option('PROGRAM_MANUAL')
        self.assertEqual(c.sent,[])
        await obj.async_select_option('PROGRAM_AUTOMATIC')
        self.assertEqual(c.sent,[('PATCH','/api/test/program','PROGRAM_AUTOMATIC')])

    async def test_activation_sends_portal_integer_values(self):
        c=Coordinator();obj=load('boiler_control.py')['BoilerActivation'](c,'heater','Kessel')
        self.assertFalse(obj.is_on);await obj.async_turn_on();await obj.async_turn_off()
        self.assertEqual(c.sent,[('PATCH','/api/test/activated',1),('PATCH','/api/test/activated',0)])

    async def test_force_charge_portal_visibility_rule(self):
        c=Coordinator();c.data['buffer']['values']['render_force_charging']=False
        obj=load('button.py')['HargassnerAction'](c,'buffer','force_charging','Puffer')
        self.assertFalse(obj.available)
        with self.assertRaises(HAError):await obj.async_press()
        self.assertEqual(c.sent,[])

class IgnitionRoutingTests(unittest.IsolatedAsyncioTestCase):
    def handler(self, coordinators):
        tree=ast.parse((COMP/'__init__.py').read_text(encoding='utf-8'))
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='handle_start_ignition')
        ns={'hass':SimpleNamespace(data={'hargassner':coordinators}),'DOMAIN':'hargassner','HargassnerCoordinator':Coordinator,'ServiceCall':object,'HomeAssistantError':HAError,'cloud_ready':caps.cloud_ready,'enabled_resource':caps.enabled_resource}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'ignition-test','exec'),ns)
        return ns['handle_start_ignition']

    async def test_only_selected_installation_receives_ignition(self):
        first=Coordinator();first.installation_id='1'
        second=Coordinator();second.installation_id='2'
        await self.handler({'a':first,'b':second})(SimpleNamespace(data={'installation_id':'2'}))
        self.assertEqual(first.sent,[])
        self.assertEqual(second.sent,[('POST','/api/test/ignite')])

    async def test_multiple_installations_require_target(self):
        first=Coordinator();first.installation_id='1'
        second=Coordinator();second.installation_id='2'
        with self.assertRaises(HAError):
            await self.handler({'a':first,'b':second})(SimpleNamespace(data={}))
        self.assertEqual(first.sent+second.sent,[])

    async def test_disabled_ignition_cannot_use_legacy_service(self):
        coord=Coordinator();coord.installation_id='1'
        coord.data['heater']['actions']['start_ignition']['disabled']=True
        with self.assertRaises(HAError):
            await self.handler({'a':coord})(SimpleNamespace(data={}))
        self.assertEqual(coord.sent,[])

if __name__=='__main__':unittest.main()
