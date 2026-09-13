"""Refill persistence, validation and forecast boundary tests."""
from datetime import date
import importlib.util
import json
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'custom_components/hargassner/pellet_ledger.py'
spec=importlib.util.spec_from_file_location('ledger',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class LedgerTests(unittest.TestCase):
    def test_backdated_refill_history_and_roundtrip(self):
        ledger=mod.PelletLedger();today=date(2026,9,13)
        ledger.record_refill('2026-09-01',2000,today)
        ledger.record_refill('2025-08-01',3000,today,'Lieferschein')
        restored=mod.PelletLedger(json.loads(json.dumps(ledger.dump())))
        self.assertEqual([r['quantity_kg'] for r in restored.refills],[3000,2000])
        self.assertEqual(sum(r['quantity_kg'] for r in restored.refills),5000)
        self.assertEqual(restored.refills[-1]['date'],'2026-09-01')

    def test_invalid_and_duplicate_deliveries(self):
        ledger=mod.PelletLedger();today=date(2026,9,13)
        for amount in (0,-1,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):ledger.record_refill('2026-09-01',amount,today)
        with self.assertRaises(ValueError):ledger.record_refill('2027-01-01',2000,today)
        ledger.record_refill('2026-09-01',2000,today)
        with self.assertRaises(ValueError):ledger.record_refill('2026-09-01',2000,today)

    def test_remove_only_selected_record(self):
        ledger=mod.PelletLedger();r=ledger.record_refill('2026-09-01',2000,date(2026,9,13))
        ledger.remove_refill(r['id']);self.assertEqual(ledger.refills,[])
        with self.assertRaises(ValueError):ledger.remove_refill(r['id'])

    def samples(self,days=7,burn=10):
        ledger=mod.PelletLedger()
        for hour in range(days*24+1):ledger.sample(hour*3600,1000+hour*burn/24,'sensor.counter')
        return ledger

    def test_forecast_is_stock_divided_by_observed_consumption(self):
        ledger=self.samples();self.assertEqual(ledger.forecast(7*mod.DAY,1000),(10,100))

    def test_no_forecast_before_three_days_or_without_burn(self):
        self.assertEqual(self.samples(2).forecast(2*mod.DAY,1000),(None,None))
        self.assertEqual(self.samples(7,0).forecast(7*mod.DAY,1000),(0,None))

    def test_invalid_stock_stale_data_and_zero_stock(self):
        ledger=self.samples()
        self.assertEqual(ledger.forecast(7*mod.DAY,None),(10,None))
        self.assertEqual(ledger.forecast(8*mod.DAY,1000),(None,None))
        self.assertEqual(ledger.forecast(7*mod.DAY,0),(10,0))

    def test_reset_gap_and_source_change_restart_learning(self):
        for timestamp,counter,source in [(7*mod.DAY+3600,1,'sensor.counter'),(8*mod.DAY,1200,'sensor.counter'),(7*mod.DAY+3600,1200,'sensor.other')]:
            ledger=self.samples();ledger.sample(timestamp,counter,source)
            self.assertEqual(len(ledger.samples),1)
            self.assertEqual(ledger.forecast(timestamp,1000),(None,None))

    def test_hourly_bound_and_rolling_window(self):
        ledger=self.samples(30)
        self.assertLessEqual(len(ledger.samples),337)
        self.assertEqual(ledger.forecast(30*mod.DAY,1000),(10,100))
        n=len(ledger.samples);ledger.sample(30*mod.DAY+60,1301,'sensor.counter')
        self.assertEqual(len(ledger.samples),n)

if __name__=='__main__':unittest.main()
