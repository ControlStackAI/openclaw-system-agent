import io
import unittest
from system_agent.tui import Interface, Cancelled

class ProtocolTests(unittest.TestCase):
    def test_late_ack_cannot_answer_a_new_prompt(self):
        ui=Interface(True,'arch')
        ui.reader=io.BytesIO(b'{"id":1,"ok":true}\n{"id":2,"value":3}\n')
        self.assertEqual(ui.receive(2),3)

    def test_cancel_does_not_consume_a_later_reply(self):
        ui=Interface(True,'arch')
        ui.reader=io.BytesIO(b'{"cancel":true}\n{"id":2,"ok":true}\n{"id":3,"value":"kept"}\n')
        with self.assertRaises(Cancelled):ui.receive(2)
        self.assertEqual(ui.receive(3),'kept')
