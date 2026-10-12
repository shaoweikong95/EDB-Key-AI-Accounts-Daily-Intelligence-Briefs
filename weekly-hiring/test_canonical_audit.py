import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
m=SourceFileLoader("canonical_audit",str(Path(__file__).with_name("canonical_audit.py"))).load_module()
class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.coverage={a:"Complete" for a in m.ACCOUNTS}
    def test_40_accounts_and_9_categories(self):
        self.assertEqual(len(m.ACCOUNTS),40)
        self.assertEqual(len(set(m.ACCOUNTS)),40)
        self.assertEqual(len(m.CATEGORIES),9)
    def test_singapore_multi_country_once(self):
        p=m.Posting("OpenAI","OpenAI","abc","https://example.com/abc","Research Scientist","Research",("Singapore","United States"),"https://example.com")
        r=m.gate([p],self.coverage,{},set(m.ACCOUNTS))
        self.assertEqual(r["singapore_total"],1)
        self.assertEqual(r["country_matrix"]["Singapore"]["Research"],1)
        self.assertEqual(r["country_matrix"]["United States"]["Research"],1)
    def test_duplicate_rejected(self):
        p=m.Posting("OpenAI","OpenAI","abc","https://example.com/abc","Research Scientist","Research",("Singapore",),"https://example.com")
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            m.gate([p,p],self.coverage,{},set(m.ACCOUNTS))
    def test_unverified_requires_diagnostic(self):
        self.coverage["OpenAI"]="Unverified"
        with self.assertRaisesRegex(ValueError,"documented"):
            m.gate([],self.coverage,{},set(m.ACCOUNTS)-{"OpenAI"})
    def test_partial_requires_verified_sg(self):
        self.coverage["OpenAI"]="Partial"
        with self.assertRaisesRegex(ValueError,"Partial"):
            m.gate([],self.coverage,{},set(m.ACCOUNTS)-{"OpenAI"})
    def test_transient_failure_threshold(self):
        failures={a:"timeout" for a in m.ACCOUNTS[:11]}
        for a in failures:self.coverage[a]="Unverified"
        with self.assertRaisesRegex(ValueError,"25%"):
            m.gate([],self.coverage,failures,set(m.ACCOUNTS)-set(failures))
if __name__=="__main__":unittest.main()
