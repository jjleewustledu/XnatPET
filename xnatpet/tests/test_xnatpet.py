import unittest
from xnatpet.xnatpet import StageXnat
import os
from uuid import uuid1

class TestPrimitives(unittest.TestCase):

    def setUp(self):
        self._cachedir='/scratch2/jjlee/Singularity'
        self.sxnat = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754', sbj='HYGLY50', ses='CNDA_E248568', scn='82')
        self.sxnat.debug_uri = True

    def test_ctor(self):
        self.assertTrue(self.sxnat, self.sxnat.__str__())
        print('\ntest_ctor\n')
        print(self.sxnat)

    def test_project(self):
        prj = self.sxnat.project
        self.assertEqual('<Project Object> CCIR_00754', str(prj))
        self.assertEqual('CCIR_00754', prj.id())
        self.assertEqual('CCIR_00754', prj.label())

    def test_subject(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        sbj = self.sxnat.subject
        self.assertEqual('<Subject Object> HYGLY50', str(sbj))
        self.assertEqual('CNDA_S58163', sbj.id())
        self.assertEqual('HYGLY50', sbj.label())

    def test_session(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        ses = self.sxnat.session
        self.assertEqual('<Experiment Object> CNDA_E248568', str(ses))
        self.assertEqual('CNDA_E248568', ses.id())
        self.assertEqual('HYGLY50_V1', ses.label())

    def test_scan(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        scn = self.sxnat.scan # URI https://cnda.wustl.edu/data/projects/CCIR_00754/experiments/CNDA_E248568/scans/82
        self.assertEqual('<Scan Object> 82', str(scn))
        self.assertEqual('82', scn.label())
        self.assertEqual('82', scn.id())

    def test_scan_dicom(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        sdcm = self.sxnat.scan_dicom
        self.assertEqual('<Resource Object> DICOM', str(sdcm))
        self.assertEqual('HYGLY50.MR.CCIR-00700_CCIR-00754_Arbelaez.82.112.20180511.081754.5x7muj.dcm', sdcm.files().get()[0])

    def test_rawdata(self):
        """after pyxnat/pyxnat/tests/resources_test.py"""
        raw = self.sxnat.rawdata
        self.assertEqual('<Resource Object> RawData', str(raw))
        self.assertEqual('1.3.12.2.1107.5.2.38.51010.2018051111574487268710305.bf',  raw.files().get()[0])
        self.assertEqual('1.3.12.2.1107.5.2.38.51010.2018051111574487268710305.dcm', raw.files().get()[4])

    # Error
    # Traceback(most
    # recent
    # call
    # last):
    # File
    # "/home2/jjlee/anaconda2/envs/xnatpet/lib/python2.7/unittest/case.py", line
    # 329, in run
    # testMethod()
    #
    #
    # File
    # "/home2/jjlee/Docker/XnatPET/xnatpet/tests/test_xnatpet.py", line
    # 55, in test_session_resources
    # self.assertEqual("['1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021.dcm']", str(res.get()))  # timing out
    # File
    # "/home2/jjlee/anaconda2/envs/xnatpet/lib/python2.7/site-packages/pyxnat/core/resources.py", line
    # 823, in get
    # return [urllib.unquote(uri_last(eobj._uri)) for eobj in self]
    # File
    # "/home2/jjlee/anaconda2/envs/xnatpet/lib/python2.7/site-packages/pyxnat/core/resources.py", line
    # 729, in __iter__
    # for eobj in self._cbase:
    #     File
    # "/home2/jjlee/anaconda2/envs/xnatpet/lib/python2.7/site-packages/pyxnat/core/resources.py", line
    # 644, in __iter__
    # eid = urllib.unquote(res[id_header])
    # KeyError: 'xnat_abstractresource_id'



class TestStaging(unittest.TestCase):

    def setUp(self):
        self._cachedir = '/scratch2/jjlee/Singularity'
        self.sxnat = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754', sbj='HYGLY50', ses='CNDA_E248568', scn='82')
        self.sxnat2 = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754', sbj='HYGLY48', ses='CNDA_E249152', scn='84') # bug in 2019 Mar-Apr; permissions to H48 lost
        self.sxnat3 = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754', sbj='HYGLY30', ses='CNDA_E193492', scn='95') # FDG UMAP
        self.sxnat.debug_uri = True
        self.sxnat2.debug_uri = True
        self.sxnat3.debug_uri = True

    def test_stage_project(self):
        constraints = [('xnat:petSessionData/DATE', '<', '2018-01-01'), 'AND']
        d = self.sxnat3.stage_project(constraints)
        print('\ntest_stage_project\n')

    def test_stage_constraints(self):
        d = self.sxnat3.stage_constraints()
        print('\ntest_stage_constraints\n')

    def test_constraints_subject(self):
        """https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570"""
        self.sxnat3.tracers = ['Fluorodeoxyglucose']
        constraints = [('xnat:petSessionData/PROJECT', '=', 'CCIR_00754'), ('xnat:petSessionData/DATE', '>', '2017-07-25'), 'AND']
        d = self.sxnat.stage_subject(None, constraints)
        print('\ntest_constraints_subject\n')

    def test_constraints_xnat(self):
        constraints = [('xnat:ctSessionData/DATE','=','2017-07-26'), 'AND']
        tbl = self.sxnat3.xnat.select(
            'xnat:ctSessionData', ['xnat:ctSessionData/SESSION_ID', 'xnat:ctSessionData/DATE']).where(constraints)
        lst = tbl.as_list()
        self.assertEqual(lst[1][0], 'CNDA_E193492')
        self.assertEqual(lst[1][1], '2017-07-26')
        print('\ntest_constraints_xnat\n')
        print(lst)

    def test_stage_subject(self):
        d = self.sxnat3.stage_subject()
        print('\ntest_stage_subject\n')

    def test_stage_session(self):
        d = self.sxnat.stage_session(self.sxnat.session)
        print('\ntest_stage_session\n')

    def test_stage_scan(self):
        d = self.sxnat.stage_scan(self.sxnat.scan)
        self.assertEqual(u'HYGLY50.MR.CCIR-00700_CCIR-00754_Arbelaez.82.155.20180511.081754.1jia62k.dcm', d.keys()[0])
        print('\ntest_stage_scan\n')
        print(d.keys()[0])
        print(d.values()[0])

    def test_stage_ct(self):
        d = self.sxnat.stage_ct(self.sxnat.session)
        self.assertEqual(u'HYGLY50.CT.Head_CCIR_00754_Arbelaez__Adult_.2.10.20180511.071309.bkca7c.dcm', d.keys()[0])
        # d{u'HYGLY48.CT.Head_CCIR_00754_Arbelaez__Adult_.2.4.20180517.114605.1ndhf3s.dcm':
        # {'URI': u'https://cnda.wustl.edu/data/experiments/CNDA_E249046/scans/2/resources/4043377/files/HYGLY48.CT.Head_CCIR_00754_Arbelaez__Adult_.2.1.20180517.114605.1ndhf0p.dcm',
        #  'absolutePath': u'https://cnda.wustl.edu/data/CNDA/archive/CCIR_00754/arc001/HYGLY48_v1_CT/SCANS/2/DICOM/HYGLY48.CT.Head_CCIR_00754_Arbelaez__Adult_.2.1.20180517.114605.1ndhf0p.dcm'}
        # }
        print('\ntest_stage_ct\n')
        print(d.keys()[0])
        print(d.values()[0])

    def test_stage_umaps(self):
        d = self.sxnat3.stage_umaps(self.sxnat.session)
        self.assertEqual(self._cachedir+'/CCIR_00754/ses-E193492/umaps/Head_MRAC_Brain_HiRes_in_UMAP_DT20170726', d[0])
        print('\ntest_stage_umaps\n')
        print(d)

    def test_stage_freesurfer(self):
        d = self.sxnat.stage_freesurfer()
        self.assertTrue(os.path.exists(d))
        print('\ntest_stage_freesurfer\n')
        print(d)



class TestSortRawData(unittest.TestCase):

    def setUp(self):
        self._cachedir = '/scratch2/jjlee/Singularity'
        self.sxnat = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir,
            prj='CCIR_00754', sbj='HYGLY50', ses='CNDA_E248568')

    def test_sort_rawdata_FDG(self):
        ses = self.sxnat.project.experiment('CNDA_E248568')
        d = self.sxnat.sort_rawdata(ses, tracer='Fluorodeoxyglucose')
        self.assertEqual(d[0], self._cachedir+'/CCIR_00754/ses-E248568/FDG_DT20180511140741.000000-Converted-NAC/1.3.12.2.1107.5.2.38.51010.30000018050718482250000000086.bf')
        print('\ntest_sort_rawdata_FDG\n')

    def test_sort_rawdata_OC(self):
        ses = self.sxnat.project.experiment('CNDA_E248568')
        d = self.sxnat.sort_rawdata(ses, tracer='Carbon')
        self.assertEqual(d[0], self._cachedir+'/CCIR_00754/ses-E248568/OC_DT20180511114714.000000-Converted-NAC/1.3.12.2.1107.5.2.38.51010.30000018050718482250000000065.bf')
        print('\ntest_sort_rawdata_OC\n')
        print(d)

    def test_sort_rawdata(self):
        ses = self.sxnat.project.experiment('CNDA_E248568')
        for t in self.sxnat.tracers:
            self.sxnat.sort_rawdata(ses, tracer=t)
        print('\ntest_sort_rawdata\n')



class TestRawData(unittest.TestCase):

    def setUp(self):
        self._cachedir = '/scratch2/jjlee/Singularity'
        self._fprefix = '1.3.12.2.1107.5.2.38.51010.30000018050718482250000000086' # 1st FDG
                      # '1.3.12.2.1107.5.2.38.51010.30000018051716493155100000021'
                      # '1.3.12.2.1107.5.2.38.51010.30000016102618254179600000045'
        self._sbj = 'HYGLY50' # 48, 30
        self._ses = 'CNDA_E248568' # CNDA_E249152, CNDA_E193492
        self._scn = 82 # 84, 95
        self.sxnat = StageXnat(
            user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'),
            cachedir=self._cachedir, prj='CCIR_00754', sbj=self._sbj, ses=self._ses, scn=self._scn)
        self.sxnat.debug_uri = True

    def _fprefix_idx(self, fp, idx):
        if idx > 9:
            return fp[:-2] + str(idx)
        else:
            return fp[:-2] + '0' + str(idx)

    def _fprefix_norm(self, fp):
        idx = int(fp[-2:])
        if idx > 9:
            return fp[:-2] + str(idx-1)
        else:
            return fp[:-1] + str(idx-1)

    def test_stage_FDG(self):
        print('\ntest_stage_FDG\n')
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Fluorodeoxyglucose')
        self.assertEqual(d[0],
            os.path.join(self.sxnat.dir_session, 'FDG_DT20180511140741.000000-Converted-NAC',
                         self._fprefix_idx(self._fprefix, 86) + '.bf')
        )
        print(d)

    def test_stage_OC(self):
        print('\ntest_stage_OC\n')
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Carbon')
        self.assertEqual(d[0],
            os.path.join(self.sxnat.dir_session, 'OC_DT.000000-Converted-NAC',
                         self._fprefix_idx(self._fprefix, 65) + '.bf')
        )
        print(d)

    def test_stage_OO(self):
        print('\ntest_stage_OO\n')
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Oxygen')
        self.assertEqual(d[0],
            os.path.join(self.sxnat.dir_session, 'OO_DT.000000-Converted-NAC',
                         self._fprefix_idx(self._fprefix, 68) + '.bf')
        )
        print(d)

    def test_stage_HO(self):
        print('\ntest_stage_HO\n')
        d = self.sxnat.stage_rawdata(self.sxnat.session, tracer='Oxygen-water')
        self.assertEqual(
            d[0],
            os.path.join(self.sxnat.dir_session, ' HO_DT20180511133140.000000-Converted-NAC',
                         self._fprefix_idx(self._fprefix, 71) + '.bf')
        )
        print(d)

    def test_stage_listmode(self):
        print('\ntest_stage_listmode\n')
        f = self._fprefix
        d = self.sxnat.stage_dicoms_rawdata(self.sxnat.session, f+'.dcm')
        self.assertEqual(f+'.dcm', d[0])
        print(d)
        d = self.sxnat.stage_bfiles_rawdata(self.sxnat.session, f+'.dcm')
        self.assertEqual(f+'.bf', d[0])
        print(d)

    def test_stage_norm(self):
        print('\ntest_stage_norm\n')
        f = self._fprefix_norm(self._fprefix)
        d = self.sxnat.stage_dicoms_rawdata(self.sxnat.session, f+'.dcm')
        self.assertEqual(f+'.dcm', d[0])
        print(d)
        d = self.sxnat.stage_bfiles_rawdata(self.sxnat.session, f+'.dcm')
        self.assertEqual(f+'.bf', d[0])
        print(d)



class TestPyxnat(unittest.TestCase):

    def setUp(self):
        from pyxnat import Interface
        self.cachedir = '/home2/jjlee/Docker/XnatPET/xnatpet/tests'
        self.xnat = Interface('https://cnda.wustl.edu', user=os.getenv('CNDA_UID'), password=os.getenv('CNDA_PWD'), cachedir=self.cachedir)
        self.experiment = self.xnat.select.project('CCIR_00754').subject('HYGLY50').experiment('CNDA_E248568')

    _modulepath = os.path.dirname(os.path.abspath(__file__))
    _id_set1 = {
        'sid': uuid1().hex,
        'eid': uuid1().hex,
        'aid': uuid1().hex,
        'cid': uuid1().hex,
        'rid': uuid1().hex,
    }

    def test_experiment(self):
        import pyxnat
        self.assertIsInstance(self.experiment, pyxnat.core.resources.Experiment)
        self.assertEqual('<Experiment Object> CNDA_E248568', str(self.experiment))

    def test_scan(self):
        import pyxnat
        scn = self.experiment.scan('82')
        self.assertIsInstance(scn, pyxnat.core.resources.Scan)
        self.assertEqual('<Scan Object> 82', str(scn))

    def test_scan_resource_dicom(self):
        import pyxnat
        res = self.experiment.scan('82').resource('DICOM')
        self.assertIsInstance(res, pyxnat.core.resources.Resource)
        self.assertEqual('<Resource Object> DICOM', str(res))

    def test_dicom(self):
        res = self.experiment.scan('82').resource('DICOM')
        csv = res.files().get()
        self.assertIsInstance(csv, list)
        self.assertEqual('HYGLY50.MR.CCIR-00700_CCIR-00754_Arbelaez.82.112.20180511.081754.5x7muj.dcm', csv[0])
        lcsv0 = os.path.join(self.cachedir, csv[0])
        res.file(csv[0]).get(lcsv0)
        self.assertTrue(os.path.exists(lcsv0))
        os.remove(lcsv0)

    def test_dicom_tempfile(self):
        import tempfile
        from uuid import uuid1
        res = self.experiment.scan('82').resource('DICOM')
        csv = res.files().get()
        lcsv0 = os.path.join(tempfile.gettempdir(), uuid1().hex)
        res.file(csv[0]).get(lcsv0)
        self.assertTrue(os.path.exists(lcsv0))
        os.remove(lcsv0)

    def test_experiment_resource_rawdata(self):
        import pyxnat
        res = self.experiment.resource('RawData')
        self.assertIsInstance(res, pyxnat.core.resources.Resource)
        self.assertEqual('<Resource Object> RawData', str(res))

    def test_bfile(self):
        res = self.experiment.resource('RawData')
        csv = res.files().get()
        self.assertIsInstance(csv, list)
        self.assertEqual('1.3.12.2.1107.5.2.38.51010.2018051111574487268710305.bf', csv[0])
        lcsv0 = os.path.join(self.cachedir, csv[0])
        res.file(csv[0]).get(lcsv0)
        self.assertTrue(os.path.exists(lcsv0))
        os.remove(lcsv0)



# N.B.:  duplicates unittest actions within pycharm
# suite = unittest.TestLoader().loadTestsFromTestCase(TestReconstruction)
# unittest.TextTestRunner(verbosity=2).run(suite)