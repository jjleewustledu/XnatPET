import unittest
from xnatpet.xnatcal import Calibration
import os
from uuid import uuid1

class TestCalibrate(unittest.TestCase):

    def setUp(self):
        self._cachedir = '/scratch/jjlee/Singularity'

    def test_create_tracerloc_list(self):
        self.cal = Calibration(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00559')
        print(self.cal.create_tracerloc_list())

        self.cal = Calibration(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754')
        print(self.cal.create_tracerloc_list())
        return