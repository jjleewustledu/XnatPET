import unittest
from xnatpet.xnatpet import StageXnat
import os
from uuid import uuid1

class TestPrimitives(unittest.TestCase):

    def setUp(self):
        self.sxnat = StageXnat(uid=os.getenv('CNDA_UID'), pwd=os.getenv('CNDA_PWD'), cch=os.getcwd())

    def test_ctor(self):
        self.assertTrue(self.sxnat, self.sxnat.__str__())
        print('\ntest_ctor\n')
        print(self.sxnat)

    def test_project(self):
        prj = self.sxnat.project
        self.assertEqual(str(prj), '<Project Object> CCIR_00754')
        self.assertEqual('CCIR_00754', prj.id())
        self.assertEqual('CCIR_00754', prj.label())

    def test_subject(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        sbj = self.sxnat.subject
        self.assertEqual(str(sbj), '<Subject Object> HYGLY48')
        self.assertEqual('CNDA_S58258', sbj.id())
        self.assertEqual('HYGLY48', sbj.label())

    def test_session(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        ses = self.sxnat.session
        self.assertEqual(str(ses), '<Experiment Object> CNDA_E249152')
        self.assertEqual('CNDA_E249152', ses.id())
        self.assertEqual('HYGLY48_V1', ses.label())

    def test_scan(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        scn = self.sxnat.scan
        self.assertEqual(str(scn), '<Scan Object> 84')
        self.assertEqual('84', scn.id())
        self.assertEqual('84', scn.label())

    def test_session_resources(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        res = self.sxnat.session.resources().files('1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm')
        self.assertEqual("['1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm']", str(res.get()))
        print('\ntest_session_resources\n')
        print(res)
        print(res.get())

    def test_scan_resources(self):
        scn = self.sxnat.scan.resources().files('HYGLY48.MR.CCIR-00700_CCIR-00754_Arbelaez.84.1.20180517.120412.uytzwe.dcm')
        self.assertEqual("['HYGLY48.MR.CCIR-00700_CCIR-00754_Arbelaez.84.1.20180517.120412.uytzwe.dcm']", str(scn.get()))
        print('\ntest_scan_resources\n')
        print(scn)
        print(scn.get())



class TestStaging(TestPrimitives):

    def test_stage_subject(self):
        d = self.sxnat.stage_subject(self.sxnat.session)
        print('\ntest_stage_session\n')

    def test_stage_sessions_after_date(self):
        """https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570"""
        constraints = [('xnat:petSessionData/DATE', '>', '2017-12-31'), 'AND']
        tbl = self.sxnat.xnat.select(
            'xnat:petSessionData', ['xnat:petSessionData/SESSION_ID', 'xnat:petSessionData/DATE']).where(constraints)
        lst = tbl.as_list() # tbl is JsonTable
        print('\ntest_stage_sessions_after_date\n')
        print(lst)
        for l in lst[1:]:
            self.sxnat.session = self.sxnat.subject.experiment(l[0])
            self.sxnat.stage_session()

    def test_stage_session(self):
        d = self.sxnat.stage_session(self.sxnat.session)
        print('\ntest_stage_session\n')

    def test_stage_scan(self):
        d = self.sxnat.stage_scan(self.sxnat.session.scan('84'))
        print('\ntest_stage_scan\n')
        print(d)

    def test_stage_ct(self):
        d = self.sxnat.stage_ct(self.sxnat.subject)
        print('\ntest_stage_ct\n')
        print(d)

    def test_stage_cts_after_date(self):
        constraints = [('xnat:ctSessionData/DATE','>','2012-09-01'), 'AND']
        tbl = self.sxnat.xnat.select(
            'xnat:ctSessionData', ['xnat:ctSessionData/SESSION_ID', 'xnat:ctSessionData/DATE']).where(constraints)
        print('\ntest_stage_ct_after_date\n')
        print(tbl.as_list())

    def test_stage_umaps(self):
        d = self.sxnat.stage_umaps(self.sxnat.session)
        print('\ntest_stage_umaps\n')
        print(d)

    def test_stage_freesurfer(self):
        d = self.sxnat.stage_freesurfer()
        print('\ntest_stage_freesurfer\n')
        print(d)

    def test_stage_rawdata_FDG(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Fluorodeoxyglucose')
        print('\ntest_stage_rawdata\n')
        print(d)

    def test_stage_rawdata_OC(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Carbon')
        print('\ntest_stage_rawdata\n')
        print(d)

    def test_stage_rawdata_OO(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Oxygen')
        print('\ntest_stage_rawdata\n')
        print(d)

    def test_stage_rawdata_HO(self):
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Oxygen-water')
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

    def test___download(self):
        self.sxnat.download()



class TestPyxnat(TestPrimitives):

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