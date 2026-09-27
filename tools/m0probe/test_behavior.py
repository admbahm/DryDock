import unittest
from behavior import evaluate
class EvidenceTests(unittest.TestCase):
 def test_memory_requires_oom_evidence(self):
  self.assertFalse(evaluate('memory',137,'',{'OOMKilled':False}))
  self.assertTrue(evaluate('memory',137,'',{'OOMKilled':True}))
 def test_missing_or_failed_disk_evidence_cannot_pass(self):
  self.assertFalse(evaluate('disk',1,'',{}))
  self.assertFalse(evaluate('disk',0,'',{}))
 def test_worker_claim_not_a_verdict(self):
  self.assertFalse(evaluate('unsupported',0,'{"passed":true}',{}))
if __name__=='__main__':unittest.main()
