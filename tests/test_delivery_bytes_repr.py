"""Bytes-repr row format (v15-k7): b'...' wrapper after the VA."""
import unittest

from gooplib.delivery import measure_delivery, row_delivers


class BytesReprTests(unittest.TestCase):
    VA = '0x14001ee20'
    PREFIX = 'zelquor and owner. delete a'

    def test_bytes_repr_row_delivers(self):
        row = f"{self.VA} b'{self.PREFIX}nd team. velocity... [truncated]"
        self.assertTrue(row_delivers(row, self.VA, self.PREFIX))

    def test_bare_and_str_repr_still_work(self):
        self.assertTrue(row_delivers(f"{self.VA} {self.PREFIX}x", self.VA, self.PREFIX))
        self.assertTrue(row_delivers(f"{self.VA} '{self.PREFIX}x", self.VA, self.PREFIX))

    def test_double_wrapper_and_wrong_va_refuse(self):
        self.assertFalse(row_delivers(f"{self.VA} b''{self.PREFIX}", self.VA, self.PREFIX))
        self.assertFalse(row_delivers(f"0x14001ee21 b'{self.PREFIX}", self.VA, self.PREFIX))
        self.assertFalse(row_delivers(f"{self.VA} b'wrong prefix", self.VA, self.PREFIX))

    def test_measure_delivery_counts_bytes_repr_slots(self):
        lines = [b'zelquor and owner. delete and byte team ticks.']
        slots = {'0': {'va': self.VA}}
        events = [f"{self.VA} b'zelquor and owner. delete and byte ... [truncated]\n"]
        self.assertEqual(measure_delivery(events, lines, slots, 1), [0])


if __name__ == '__main__':
    unittest.main()
