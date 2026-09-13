"""History manager rollback and source handling with HA services mocked."""
import ast
import asyncio
from datetime import datetime,timezone,date
from pathlib import Path
from types import SimpleNamespace
import unittest
from test_pellet_ledger import mod
from test_energy import energy

class FakeStore:
    def __init__(self,*args):self.saved=None;self.fail=False
    async def async_save(self,data):
        if self.fail:raise OSError('disk failure')
        import copy
        self.saved=copy.deepcopy(data)
    def async_delay_save(self,fn,delay):pass

class HistoryManagerTests(unittest.IsolatedAsyncioTestCase):
    def create(self):
        path=Path(__file__).resolve().parents[1]/'custom_components/hargassner/pellet_history.py'
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        import copy
        ns={'Store':FakeStore,'DOMAIN':'hargassner','PelletLedger':mod.PelletLedger,'asyncio':asyncio,'callback':lambda f:f,'copy':copy,'nonnegative':mod.nonnegative,'pellet_energy_kwh':energy.pellet_energy_kwh,'CONF_PELLET_CONSUMPTION_ENTITY':'pellet_consumption_entity','STOCK_SOURCE':'pellet_stock_entity','dt_util':SimpleNamespace(utcnow=lambda:datetime.now(timezone.utc),now=lambda:datetime.now(timezone.utc))}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'history-test','exec'),ns)
        states={'sensor.kg':SimpleNamespace(state='6548',attributes={'unit_of_measurement':'kg','state_class':'total_increasing'})}
        hass=SimpleNamespace(states=SimpleNamespace(get=states.get));entry=SimpleNamespace(entry_id='test',options={'pellet_consumption_entity':'sensor.kg'})
        coord=SimpleNamespace(last_update_success=True,data={'_online':True,'heater':{'widget_type':'HEATER','values':{'fuel_stock':3385}}})
        return ns['PelletHistory'](hass,entry,coord),states

    async def test_record_persists_without_changing_stock_or_counter(self):
        h,states=self.create();h.update()
        await h.edit_refill({'date':'2025-01-01','quantity_kg':2000})
        self.assertEqual(h.stock,3385);self.assertEqual(h.counter,6548)
        self.assertEqual(len(h.store.saved['refills']),1)

    async def test_failed_save_rolls_back_delivery(self):
        h,_=self.create();h.store.fail=True
        with self.assertRaises(OSError):await h.edit_refill({'date':'2025-01-01','quantity_kg':2000})
        self.assertEqual(h.ledger.refills,[])

    async def test_offline_cloud_stock_and_invalid_source_not_zero(self):
        h,states=self.create();h.update();self.assertEqual(h.stock,3385)
        h.coordinator.data['_online']=False;states['sensor.kg'].state='unavailable';h.update()
        self.assertIsNone(h.stock);self.assertIsNone(h.counter)

if __name__=='__main__':unittest.main()
