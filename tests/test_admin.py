import unittest
from unittest.mock import patch
from system_agent.admin import create_plan, execution_argv


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.facts = {'phase': 'installed-candidate', 'boot_id': 'boot-one'}
        self.policy = {'datasets': ['pool/data']}

    def test_scope_and_no_erase(self):
        with self.assertRaises(ValueError):
            create_plan('snapshot', 'pool/other', self.policy, self.facts)
        with self.assertRaises(ValueError):
            create_plan('erase', 'pool/data', self.policy, self.facts)

    @patch('system_agent.admin.identity', return_value='dataset-guid-one')
    def test_exact_approval_expiry_boot_and_resource(self, identity):
        plan = create_plan('snapshot', 'pool/data', self.policy, self.facts, now=10)
        argv = execution_argv(plan, self.policy, self.facts, plan['digest'], now=11)
        self.assertEqual(argv[:2], ['zfs', 'snapshot'])
        self.assertTrue(argv[2].startswith('pool/data@controlstack-'))
        for approval, facts, now in [('wrong', self.facts, 11), (plan['digest'], self.facts, 400),
                                      (plan['digest'], {**self.facts, 'boot_id': 'new'}, 11)]:
            with self.assertRaises(ValueError):
                execution_argv(plan, self.policy, facts, approval, now=now)
        identity.return_value = 'replaced-resource'
        with self.assertRaises(ValueError):
            execution_argv(plan, self.policy, self.facts, plan['digest'], now=11)

    @patch('system_agent.admin.identity', return_value='dataset-guid-one')
    def test_policy_revocation_invalidates_plan(self, identity):
        plan = create_plan('snapshot', 'pool/data', self.policy, self.facts, now=10)
        with self.assertRaises(ValueError):
            execution_argv(plan, {}, self.facts, plan['digest'], now=11)
