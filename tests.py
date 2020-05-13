import unittest

import log_analyzer


class ParserTest(unittest.TestCase):
    # def setUp(self) -> None:
    #     us = nginx_parser.UrlStat('/api/v2/banner/25019354', 0.390)

    def test_log_analyzer(self):
        """assert that input parameter is file, not a directory"""
        with self.assertRaises(IsADirectoryError):
            log_analyzer.log_analyze('some_dir.log.gz')

        """assert that input parameter is file, and file exist"""
        with self.assertRaises(FileNotFoundError):
            log_analyzer.log_analyze('nginx-some_log.log.gz')

        """assert that output object is dictionary"""
        self.assertIs(type(log_analyzer.log_analyze('nginx-access-ui.log.gz')), dict)

        """assert that output object is iterable and not empty"""
        self.assertTrue(len(log_analyzer.log_analyze('nginx-access-ui.log.gz')))


if __name__ == '__main__':
    unittest.main()
