"""Persistent pellet ledger and conservative rolling consumption forecast."""
from datetime import date
from math import isfinite
from uuid import uuid4

DAY = 86400
WINDOW = 14 * DAY
MIN_SPAN = 3 * DAY
MAX_GAP = 6 * 3600


def nonnegative(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return value if isfinite(value) and value >= 0 else None


class PelletLedger:
    def __init__(self, data=None):
        data = data or {}
        self.refills = list(data.get('refills', []))
        self.samples = list(data.get('samples', []))
        self.source = data.get('source')

    def dump(self):
        return {'refills': self.refills, 'samples': self.samples, 'source': self.source}

    def record_refill(self, filled_on, quantity, today, note=''):
        filled = date.fromisoformat(filled_on)
        amount = nonnegative(quantity)
        if amount is None or amount <= 0 or filled > today:
            raise ValueError('Datum darf nicht in der Zukunft liegen; Menge muss positiv sein.')
        if any(r['date'] == filled.isoformat() and r['quantity_kg'] == amount for r in self.refills):
            raise ValueError('Diese Befüllung ist bereits eingetragen.')
        record = {'id': str(uuid4()), 'date': filled.isoformat(), 'quantity_kg': amount, 'note': str(note)[:200]}
        self.refills.append(record)
        self.refills.sort(key=lambda r: (r['date'], r['id']))
        return record

    def remove_refill(self, record_id):
        records = [r for r in self.refills if r['id'] != record_id]
        if len(records) == len(self.refills):
            raise ValueError('Befüllung nicht gefunden.')
        self.refills = records

    def sample(self, timestamp, counter, source):
        counter = nonnegative(counter)
        if counter is None:
            return False
        if self.source != source:
            self.source, self.samples = source, []
        if self.samples and (timestamp < self.samples[-1]['ts'] or counter < self.samples[-1]['kg'] or timestamp-self.samples[-1]['ts'] > MAX_GAP):
            self.samples = []  # Counter reset, clock jump or long missing interval.
        if self.samples and timestamp-self.samples[-1]['ts'] < 3600:
            return False
        self.samples.append({'ts': timestamp, 'kg': counter})
        self.samples = [s for s in self.samples if timestamp-s['ts'] <= WINDOW]
        return True

    def forecast(self, timestamp, stock):
        stock = nonnegative(stock)
        if len(self.samples) < 2 or timestamp-self.samples[-1]['ts'] > MAX_GAP:
            return None, None
        start, end = self.samples[0], self.samples[-1]
        span = end['ts']-start['ts']
        if span < MIN_SPAN:
            return None, None
        rate = (end['kg']-start['kg']) / (span / DAY)
        if rate < 0 or not isfinite(rate):
            return None, None
        days = stock/rate if stock is not None and rate > 0 else None
        return round(rate, 3), round(days, 1) if days is not None else None
