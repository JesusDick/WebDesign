import unittest

from hello import sayhello

class SayHelloTestCase(unittest.TestCase):  # 測試用例
    def setUp(self):  # 測試固件
        pass

    def tearDown(self):  # 測試固件
        pass

    def test_sayhello(self):  # 第 1 個測試
        rv = sayhello()
        self.assertEqual(rv, 'Hello!')
    
    def test_sayhello_to_somebody(self):
        rv = sayhello(to='Grey')
        self.assertEqual(rv, 'Hello, Grey!')

if __name__ == '__main__':
    unittest.main()