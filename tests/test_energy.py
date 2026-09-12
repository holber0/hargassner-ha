"""Energy accounting and event-driven updates without a live HA instance."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

COMP = Path(__file__).resolve().parents[1] / 'custom_components/hargassner'
spec = importlib.util.spec_from_file_location('energy_math', COMP / 'energy.py')
energy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(energy)

class EnergyTests(unittest.TestCase):
    def test_known_counter(self):
        self.assertEqual(energy.pellet_energy_kwh('6548','kg','total_increasing'),31430.4)

    def test_consumption_delta(self):
        first=energy.pellet_energy_kwh('6548','kg','total_increasing')
        second=energy.pellet_energy_kwh('6558','kg','total_increasing')
        self.assertAlmostEqual(second-first,48)

    def test_bad_readings_never_become_zero(self):
        for value in (None,'unknown','unavailable','nan','inf','-inf','-1',True,'1e309'):
            with self.subTest(value=value):
                self.assertIsNone(energy.pellet_energy_kwh(value,'kg','total_increasing'))

    def test_stock_wrong_unit_and_non_counter_rejected(self):
        for unit,state_class in [('kg','total'),('kg','measurement'),('t','total_increasing'),(None,'total_increasing')]:
            self.assertIsNone(energy.pellet_energy_kwh('3385',unit,state_class))

    def test_real_reset_and_zero_are_forwarded(self):
        self.assertEqual(energy.pellet_energy_kwh('0','kg','total_increasing'),0)
        self.assertEqual(energy.pellet_energy_kwh('2','kg','total_increasing'),9.6)

    def test_sensor_event_lifecycle(self):
        source=ast.parse((COMP/'energy_sensor.py').read_text(encoding='utf-8-sig'))
        source.body=[node for node in source.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
        class Sensor:
            async def async_added_to_hass(self): pass
            def async_on_remove(self,cb): self.remove_callback=cb
            def async_write_ha_state(self): self.writes+=1
        callbacks=[]
        def track(hass,entities,callback):
            callbacks.append((entities,callback))
            return lambda: callbacks.clear()
        namespace={'SensorEntity':Sensor,'SensorDeviceClass':SimpleNamespace(ENERGY='energy'),'SensorStateClass':SimpleNamespace(TOTAL_INCREASING='total_increasing'),'UnitOfEnergy':SimpleNamespace(KILO_WATT_HOUR='kWh'),'callback':lambda f:f,'DeviceInfo':dict,'DOMAIN':'hargassner','PELLET_ENERGY_KWH_PER_KG':4.8,'pellet_energy_kwh':energy.pellet_energy_kwh,'async_track_state_change_event':track}
        exec(compile(source,'energy_sensor.py','exec'),namespace)
        cls=namespace['PelletEnergySensor'];coord=SimpleNamespace(installation_id='test',installation_name='Test')
        obj=cls(coord,'sensor.consumption'); states={};obj.hass=SimpleNamespace(states=SimpleNamespace(get=states.get));obj.writes=0
        import asyncio
        asyncio.run(obj.async_added_to_hass())
        self.assertFalse(obj._attr_available)
        states['sensor.consumption']=SimpleNamespace(state='6548',attributes={'unit_of_measurement':'kg','state_class':'total_increasing'})
        callbacks[0][1](None)
        self.assertEqual(obj._attr_native_value,31430.4)
        self.assertTrue(obj._attr_available)
        self.assertEqual(obj.writes,1)
        states['sensor.consumption'].state='unavailable';callbacks[0][1](None)
        self.assertFalse(obj._attr_available)
        self.assertIsNone(obj._attr_native_value)
        self.assertNotEqual(obj._attr_unique_id,cls(coord,'sensor.other')._attr_unique_id)
        self.assertEqual(obj._attr_state_class,'total_increasing')
        obj.remove_callback();self.assertEqual(callbacks,[])

if __name__=='__main__': unittest.main()
