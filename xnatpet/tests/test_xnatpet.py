import unittest
from xnatpet.xnatpet import StageXnat
import os
from uuid import uuid1

class TestStageXnat(unittest.TestCase):

    def setUp(self):
        self.sxnat = StageXnat(uid=os.getenv('CNDA_UID'), pwd=os.getenv('CNDA_PWD'), cch=os.getcwd())

    def test_ctor(self):
        self.assertTrue(self.sxnat, self.sxnat.__str__())
        print('\ntest_ctor\n')

    def test_project(self):
        prj = self.sxnat.project
        print('\ntest_project\n')
        print(prj.get())

    def test_subject(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        sbj = self.sxnat.subject
        print('\ntest_subject\n')
        print(sbj) # .get() -> lengthy xml

    def test_session_resources(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        res = self.sxnat.session.resources().files('1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        print('\ntest_session_resources\n')
        print(res.get())

    def test_scan_resources(self):
        sxnat = StageXnat(uid=os.getenv('CNDA_UID'), pwd=os.getenv('CNDA_PWD'), cch=os.getcwd(),
                          scn='84')
        scn = sxnat.scan.resources().files('HYGLY48.MR.CCIR-00700_CCIR-00754_Arbelaez.84.1.20180517.120412.uytzwe.dcm')
        print('\ntest_scan_resources\n')
        print(scn.get())

    def test_stage_rawdata_FDG(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Fluorodeoxyglucose')
        print('\ntest_stage_rawdata\n')
        print(d)

    def test_stage_rawdata_OC(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Carbon')
        print('\ntest_stage_rawdata\n')
        print(d)

    def test_stage_dicoms_rawdata_listmode(self):
        d = self.sxnat.stage_dicoms_rawdata(self.sxnat.session, '1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        print('\ntest_stage_dicoms_rawdata\n')
        print(d)

    def test_stage_bfiles_rawdata_listmode(self):
        d = self.sxnat.stage_bfiles_rawdata(self.sxnat.session, '1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        print('\ntest_stage_bfiles_rawdata\n')
        print(d)

    def test_stage_dicoms_rawdata_norm(self):
        d = self.sxnat.stage_dicoms_rawdata(self.sxnat.session, '1.3.12.2.1107.5.2.38.51010.30000018051716493155100000020.dcm')
        print('\ntest_stage_dicoms_rawdata\n')
        print(d)

    def test_stage_bfiles_rawdata_norm(self):
        d = self.sxnat.stage_bfiles_rawdata(self.sxnat.session, '1.3.12.2.1107.5.2.38.51010.30000018051716493155100000020.dcm')
        print('\ntest_stage_bfiles_rawdata\n')
        print(d)



class TestPyxnat(TestStageXnat):

    _modulepath = os.path.dirname(os.path.abspath(__file__))
    _id_set1 = {
        'sid': uuid1().hex,
        'eid': uuid1().hex,
        'aid': uuid1().hex,
        'cid': uuid1().hex,
        'rid': uuid1().hex,
    }

    def test_get_file(self):
        res = self.sxnat.xnat.select.project('CCIR_00754').subject('HYGLY48').experiment('CNDA_E249152').resources()
        fil = res.files('1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        fpath = fil.get()
        assert(os.path.exists(fpath))

    def test_get_copy_file(self):
        import tempfile
        from uuid import uuid1
        fpath = os.path.join(tempfile.gettempdir(), uuid1().hex)
        res = self.sxnat.xnat.select.project('CCIR_00754').subject('HYGLY48').experiment('CNDA_E249152').resources()
        fil = res.file('1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        fpath = fil.get_copy(fpath)
        assert(os.path.exists(fpath))

    def test_get_zip(self):
        """
        After pyxnat/pyxnat/tests/resources_test.py.
        Direct URL:  '/data/projects/CCIR_00754/subjects/HYGLY48/experiments/CNDA_E249152/resources/4046925/files/1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm'
        """
        subj_1 = self.sxnat.xnat.select.project('CCIR_00754').subject('HYGLY48').experiment('CNDA_E249152') # self._id_set1['sid'])
        r = subj_1.resources().files('1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        local_dir = os.path.join(self._modulepath, 'test_zip_download')
        if not os.path.exists(local_dir):
            os.mkdir(local_dir)

        rout = r.get(object)[0] # local_dir, extract=True
        print('\ntest_get_zip\n')
        print(rout)
        #print(rout.json())
        #print(rout.json()["ResultSet"]["Result"])

    def test_petScanData(self):
        scn = self.sxnat.xnat.array.scans(project_id='CCIR_00754',
                                          experiment_id='CNDA_E249152',
                                          scan_type='xnat:mrScanData')
        print('\ntest_petScanData\n')
        print(scn)

    def test_simple_level_expand(self):
        from pyxnat import select
        expanded = select.compute('/projects/CCIR_00754/subjects/HYGLY48//experiments')
        print(expanded)







# N.B.:  duplicates unittest actions within pycharm
# suite = unittest.TestLoader().loadTestsFromTestCase(TestReconstruction)
# unittest.TextTestRunner(verbosity=2).run(suite)