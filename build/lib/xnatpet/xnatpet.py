import os
import errno

import pyxnat

class StageXnat(object):
    """Uses pyxnat or requests packages to interact with an XNAT REST API to download data from
       projects, subjects, sessions/experiments, scans, rawdata-resources and freesurfer-assessors."""

    __author__ = "John J. Lee"
    __copyright__ = "Copyright 2019"

    project = None
    subject = None
    session = None
    scan = None
    sleep_duration = 600 # secs
    tracers = ['Oxygen-water', 'Carbon', 'Oxygen'] # 'Fluorodeoxyglucose'

    @property
    def str_project(self):
        return self.project.id()

    @property
    def str_subject(self):
        return self.subject.id() # + '-' + self.subject.label()

    @property
    def str_session(self):
        return str(self.session)[20:]

    @property
    def str_scan(self):
        return self.scan.id()

    @property
    def dir_project(self):
        return os.path.join(self.builddir, self.str_project)

    @property
    def dir_subject(self):
        import string
        lst = string.split(self.str_subject, '_', 1)
        return os.path.join(self.dir_project, 'sub-'+lst[1]) # + '-' + self.subject.label())

    @property
    def dir_session(self):
        import string
        lst = string.split(self.str_session, '_', 1)
        return os.path.join(self.dir_subject, 'ses-'+lst[1])

    @property
    def dir_SCANS(self):
        return os.path.join(self.dir_session, 'SCANS')

    @property
    def dir_scan(self):
        return os.path.join(self.dir_SCANS, self.str_scan)

    @property
    def dir_ct(self):
        return os.path.join(self.dir_session, 'ct')

    @property
    def dir_umaps(self):
        return os.path.join(self.dir_session, 'umaps')

    @property
    def dir_rawdata(self):
        return os.path.join(self.dir_session, 'rawdata')



    # PRIMITIVES #########################################################################

    def projects(self, interface=None, glob='*'):
        """
        :param interface:
        :return all pyxnat.projects for XNAT interface:
        """
        if interface:
            self.xnat = interface
        return self.xnat.projects(glob)

    def subjects(self, prj=None, glob='*'):
        """
        :param prj:
        :return all pyxnat.subjects for project:
        """
        if prj:
            self.project = prj
        return self.project.subjects(glob)

    def sessions(self, sbj=None, glob='*'):
        """
        :param sbj:
        :return all pyxnat.experiments for subject:
        """
        if sbj:
            self.subject = sbj
        return self.subject.experiments(glob)

    def scans(self, ses=None, glob='*'):
        """
        :param ses:
        :return all pyxnat.session.scans for session:
        """
        if ses:
            self.session = ses
        return self.session.scans(glob)



    # STAGING #########################################################################

    def stage_constraints(self, constraints=None, modal='pet'):
        """synonym for stage_project"""
        return self.stage_project(constraints, modal)

    def stage_project(self, constraints=None, modal='pet'):
        """
        https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570
        :param constraints, e.g., constraints = [('xnat:petSessionData/DATE', '>', '2017-12-31'), 'AND']:
        :param modal from 'pet', 'mr', 'ct':
        :param all_scans is bool:
        :return:
        """
        for s in self.subjects():
            self.stage_subject(s, constraints, modal)
        return

    def stage_subject(self, sbj=None, constraints=None, modal='pet'):
        """
        https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570
        :param sbj is a pyxnat subject:
        :param constraints, e.g., constraints = [('xnat:petSessionData/DATE', '>', '2017-12-31'), 'AND']:
        :param modal from 'pet', 'mr', 'ct':
        :param all_scans is bool:
        :return:
        """
        if sbj:
            self.subject = sbj
        if not constraints:
            for s in self.sessions(self.subject):
                self.stage_session(s)
            return

        tbl = self.xnat.select(
            'xnat:%sSessionData'%modal,
            ['xnat:%sSessionData/SESSION_ID'%modal, 'xnat:%sSessionData/DATE'%modal]).where(constraints)
        lst = tbl.as_list() # tbl is JsonTable
        for l_ in lst[1:]:
            self.session = self.subject.experiment(l_[0])
            self.stage_session(self.session)
        return

    def stage_session(self, ses=None):
        """
        https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570
        :param ses is a pyxnat experiment:
        :param all_scans is bool:
        :return:
        """
        while self.on_schedule() and not self.__resources_available():
            self.__wait()

        if ses:
            self.session = ses
        self.stage_scan(self.scans()[0]) # default scan will be ignored by stage_rawdata
        self.stage_ct(self.subject)
        self.stage_freesurfer()
        #self.stage_umaps()
        #for s in self.scans():
        #    self.stage_scan(s)
        for t in self.tracers:
            self.stage_rawdata(self.session, t)
        return

    def stage_scan(self, scn=None, ses=None, sdir=None):
        if scn:
            self.scan = scn
        if not ses:
            ses = self.session
        if not sdir:
            sdir = self.dir_scan
        return self.stage_dicoms_scan(self.scan, ses=ses, ddir=sdir)

    def stage_ct(self, obj):
        # recursion for Subjects
        if isinstance(obj, pyxnat.core.resources.Subject):
            addict = None
            for e in self.sessions(obj):
                ddict = self.stage_ct(e)
                if ddict:
                    addict = ddict
            return addict

        # base case for Experiment
        if isinstance(obj, pyxnat.core.resources.Experiment):
            if self.session_has_ct(obj):
                ctdir = self.dir_ct
                return self.stage_dicoms_scan(obj.scans('2')[0], ses=obj, ddir=ctdir)
            return
        raise AssertionError("stage_ct could not find a ct sessions for %s" % str(obj))

    def stage_umaps(self, ses=None, umap_desc=u'Head_MRAC_Brain_HiRes_in_UMAP'):
        """
        downloads .dcm files for all umaps from a session, saving to a folder named self.umap_desc
        :param ses is a pyxnat session (a.k.a., experiment):
        :param umap_desc is a pydicom SeriesDescription:
        :return upaths is a list of umap path names:
        """
        from pydicom.errors import InvalidDicomError
        from warnings import warn
        if not ses:
            ses = self.session
        upaths = []
        scans = ses.scans('*')
        for s in scans:
            try:
                dinfo = self.stage_dicom0_scan(s)
                if umap_desc == dinfo.SeriesDescription:
                    ds = s.resources().files('*.dcm').get()
                    self.__download_scan(ds, self.__get_dicomdict, sessid = ses.id(), scanid=s.id())
                    upaths.append(
                        self.move_scan(self.dir_scan, self.dir_umaps, scaninfo=dinfo))
            except (IOError, InvalidDicomError, TypeError) as e:
                warn(e.message)
        return upaths

    def stage_dicom0_scan(self, scn, fs='*.dcm'):
        """
        stages 0th DICOM for header information for scan
        :param scn: 
        :param fs: 
        :return dicom info from pydicom.dcdmread: 
        """
        import pydicom
        self.scan = scn
        ds = scn.resources().files(fs).get()
        ds0 = os.path.join(self.dir_scan, ds[0])
        if not os.path.exists(ds0):
            self.__download_files([ds[0]], self.__get_dicomdict, scanid=scn.id())
        return pydicom.dcmread(os.path.join(self.dir_scan, ds[0]))

    def stage_dicoms_scan(self, scn=None, ses=None, fs='*.dcm', ddir=None):
        """
        stages all DICOMs for a scan
        :param scn:
        :param ses:
        :param fs:
        :param ddir:
        :return __download_scan():
        """
        if scn:
            self.scan = scn
        if not ses:
            ses = self.session
        if not ddir:
            ddir = self.dir_scan
        ds = self.scan.resources().files(fs).get()
        return self.__download_scan(ds, self.__get_dicomdict, sessid=ses.id(), scanid=self.scan.id(), fdir=ddir)

    def stage_rawdata(self, ses=None, tracer='Fluorodeoxyglucose'):
        """
        downloads and arranges session rawdata as .dcm files in class param dir_rawdata and
        .bf files according to final destinations chosen by class methods move_rawdata and rawdata_destination
        :param ses is a pyxnat experiment:
        :param tracer from class param tracers:
        :return dests is list of downloaded rawdata in final destinations:
        """
        while self.on_schedule() and not self.__resources_available():
            self.__wait()

        if ses:
            self.session = ses
        if not os.path.exists(self.dir_rawdata):
            os.makedirs(self.dir_rawdata)
        os.chdir(self.dir_rawdata)
        ds = self.stage_dicoms_rawdata(self.session)
        bs = self.stage_bfiles_rawdata(self.session, ds0=ds, tracer=tracer) # all .dcm -> .bf
        dests = []
        for b in bs:
            dests.append(self.move_rawdata(self.filename2bf(b), tracer))
            dests.append(self.move_rawdata(self.filename2dcm(b), tracer)) # .dcm has information needed by move_rawdata
        return dests

    def stage_dicoms_rawdata(self, ses=None, ds0='*.dcm'):
        """
        downloads all .dcm files from session resources RawData to class param dir_rawdata;
        these may be parsed in further actions
        :param ses is a pyxnat experiment:
        :param ds0 is a string specifier for requests from ses:
        :return ds is the list of downloaded DICOM filenames:
        """
        if ses:
            self.session = ses
        ds = self.session.resources().files(ds0).get()
        self.__download_files(ds, self.__get_rawdatadict, fdir=self.dir_rawdata)
        return ds

    def stage_bfiles_rawdata(self, ses=None, ds0='*.dcm', tracer='Fluorodeoxyglucose'):
        """
        downloads .bf files from the session resources RawData to class param dir_rawdata
        :param ses is a pxnat session experiment:
        :param ds0 is a string specifier for requests from sess or a list of specifiers or a list of files:
        :param tracer is from class param tracers:
        :return bs is the list of downloaded .bf files:
        """
        if ses:
            self.session = ses
        if not ds0:
            return False
        ds = []
        if isinstance(ds0, str):
            ds = self.session.resources().files(ds0).get() # expands specifier ds0
        if isinstance(ds0, list):
            for f in ds0:
                ds.append(self.session.resources().files(f).get()) # expands f as needed
            ds = [item for sublist in ds for item in sublist] # flattens list of lists
            # From Alex Martelli
            # https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-list-of-lists?page=1&tab=votes#tab-top

        bs = self.__select_tracer(ds, tracer)
        bs = self.__select_bfiles(bs)
        self.__download_files(bs, self.__get_rawdatadict, fdir=self.dir_rawdata)
        return bs

    def stage_freesurfer(self):
        """
        downloads assessors labeled freesurfer from a session
        :return __download_assessors():
        """
        from glob2 import glob
        fs = glob(os.path.join(self.dir_session, self.str_session + '_freesurfer_*'))
        if fs and os.path.isdir(fs[0]):
            return
        return self.__download_assessors()



    # UTILITIES #############################################################################

    def dcm_acquisitiontime(self, dcm):
        """
        provides best estimate of start time (GMT) of MR sequences
        :param dcm filename:
        :return:
        """
        d = self.__get_dicom(dcm)
        return d.StudyTime # hhmmss.ffffff after http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html

    def dcm_seriesdate(self, dcm):
        d = self.__get_dicom(dcm)
        return d.SeriesDate # yyyymmdd

    def dcm_seriestime(self, dcm):
        """
        provides best estimate of end time (GMT) of MR sequences;
        provides best estimate of start time (local) of listmode collection
        :param dcm:
        :return:
        """
        d = self.__get_dicom(dcm)
        return d.SeriesTime # hhmmss.ffffff after http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html

    def dcm_studytime(self, dcm):
        """
        provides best estimate of time (local) of norm?
        :param dcm filename:
        :return:
        """
        d = self.__get_dicom(dcm)
        return d.StudyTime # hhmmss.ffffff after http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html

    def ensuredir(self, d):
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        else:
            return d

    def filename2dcm(self, bf):
        from os import path
        (root,ext) = path.splitext(bf)
        return root + ".dcm"

    def filename2bf(self, dcm):
        from os import path
        (root,ext) = path.splitext(dcm)
        return root + ".bf"

    def ifh_imageduration(self, dcm):
        lm_dict = self.__get_interfile(dcm)
        return lm_dict['image duration']['value'] # sec

    def ifh_studydate(self, dcm):
        lm_dict = self.__get_interfile(dcm)
        return lm_dict['study date']['value'] # yyyy:mm:dd

    def ifh_studytime(self, dcm):
        lm_dict = self.__get_interfile(dcm)
        return lm_dict['study time']['value'] # hh:mm:ss GMT+00:00

    def ifh_tracer(self, dcm):
        lm_dict = self.__get_interfile(dcm)
        return lm_dict['Radiopharmaceutical']['value']

    def is_norm(self, dcm):
        return self.__is_imagetype3(dcm, 'PET_NORM')

    def is_listmode(self, dcm):
        return self.__is_imagetype3(dcm, 'PET_LISTMODE')

    def is_tracer(self, dcm, tracer):
        import re
        with open(dcm, 'r') as fid:
            fcontent = fid.read()
        p = re.compile('(?<=Radiopharmaceutical:)[A-Za-z\-]+')
        m = re.search(p, fcontent)
        return m.group(0) == tracer

    def is_umap(self, dcm):
        d = self.__get_dicom(dcm)
        return d.SeriesDescription == u'Head_MRAC_Brain_HiRes_in_UMAP'

    def move_rawdata(self, rfile0, tracer):
        """
        moves rawdata original file, .dcm or .bf, to file in new target directory
        :param rfile0 is the originating file:
        :param tracer from class param tracers:
        :return rfile:
        """
        from os import path
        import shutil
        rtarg = self.rawdata_destination(rfile0, tracer)
        self.ensuredir(rtarg)
        rfile = path.join(rtarg, path.basename(rfile0))
        shutil.move(rfile0, rfile)
        return rfile

    def move_scan(self, spath0, starg, scaninfo):
        """
        moves .dcm from originating scan path (:= scaninfo) to new target scan path (:= scaninfo)
        :param spath0 is the originating path containing .dcm:
        :param starg is a target path:
        :param scaninfo := pydicom.dcmread():
        :return spath:
        """
        from os import path
        import shutil
        self.ensuredir(starg)
        spath = path.join(starg,
                          str(scaninfo.SeriesDescription) + '_DT' +
                          str(scaninfo.SeriesDate) +
                          str(scaninfo.AcquisitionTime))
        if os.path.exists(spath):
            shutil.rmtree(spath)
        shutil.move(spath0, spath)
        return spath

    def on_schedule(self):
        return True

    def rawdata_destination(self, b, tracer):
        """
        determines canonical directory name by reading DICOM for rawdata
        :param b:
        :param tracer:
        :return canonical rawdata directory:
        """
        dest = os.path.join(
            self.dir_session,
            self.tracer_label(tracer, b) + '_' + self.visit_label(b) + '-Converted-NAC')
        return dest

    def session_has_ct(self, ses):
        if not ses:
            ses = self.session
        file_list = ses.scans('2').resources().files('*.dcm').get()
        if not file_list:
            return False
        return '.CT.Head' in file_list[0]

    def tracer_label(self, t, b):
        from pydicom import dcmread
        d = dcmread(self.filename2dcm(b))
        return {
            'Fluorodeoxyglucose': 'FDG',
            'Carbon': 'OC',
            'Oxygen': 'OO',
            'Oxygen-water': 'HO',
        }[t]

    def visit_label(self, b):
        from pydicom import dcmread
        d = dcmread(self.filename2dcm(b))
        return 'DT' + d.StudyDate + d.SeriesTime # str DTYYYYMMDDhhmmss.xxxxxx




    # CLASS-PRIVATE #########################################################################

    def __download_assessors(self, variety='ALL', vtype='files'):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :variety is the value for assessors in the XNAT REST API:
        :vtype is the variety type:
        :return filesystem with archive unpacked to self.dir_session && creation of symlink to freesurfer mri
        """
        from shutil import copyfileobj
        from zipfile import ZipFile
        from glob2 import glob

        cookie = self.__jsession_request()
        uri = self.host + "/data/experiments/%s/assessors/%s/%s?format=zip" % (self.str_session, variety, vtype)
        zip = 'assessors_%s_%s.zip' % (variety, vtype)
        mri = os.path.join(self.dir_session, 'mri')

        try:
            self.ensuredir(self.dir_session)
            os.chdir(self.dir_session)
            with open(zip, 'wb') as f:
                r = self.__get_url(uri, headers=cookie, verify=False, stream=True)
                copyfileobj(r.raw, f)
            z = ZipFile(zip, 'r')
            z.extractall(self.dir_session)
            z.close()
            os.remove(zip)
            p = glob(os.path.join('CNDA*freesurfer*', 'out', 'resources', 'DATA', 'files', '*', 'mri'))
            os.symlink(p[0], mri)
            print('Downloaded assessors %s to %s.\n' % (uri, zip))
        except IOError as e:
            raise AssertionError(e.message)

        self.__jsession_expire(cookie)
        return mri

    def __download_scan(self, fnames, get_datadict, sessid=None, scanid=None, fdir=None):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :param fnames are file names:
        :param get_datadict is a function that returns fdict and fdir:
        :param sessid is str:
        :param scanid is str:
        :param fdir is a filesystem path:
        :return dict from get_datadict:
        """
        from warnings import warn

        cookie = self.__jsession_request()
        if not sessid:
            sessid = self.str_session
        if not scanid:
            scanid = self.str_scan
        if not fdir:
            fdir = self.__get_dicomdir(scanid)
        self.ensuredir(fdir)
        os.chdir(fdir)
        print('\n__download_scan:  session %s, scan %s.\n' % (sessid, scanid))
        ddict = get_datadict(cookie, sessid=sessid, scanid=scanid)
        for j, (name, path_dict) in enumerate(ddict.iteritems()):
            #print("downloading file %s to %s." % (name, fdir))
            try:
                with open(name, 'wb') as f:
                    r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                    for block in r.iter_content(1024):
                        if not block:
                            break
                        f.write(block)
            except IOError as e:
                warn('fname must be a filename; dest must be a directory')
                raise AssertionError(e.message)

        self.__jsession_expire(cookie)
        return ddict

    def __download_files(self, fnames, get_datadict, sessid=None, scanid=None, fdir=None):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :param fnames are file names:
        :param get_datadict is a function that returns fdict and fdir:
        :param sessid is str:
        :param scanid is str:
        :param fdir is a filesystem path:
        :return dict from get_datadict:
        """
        from warnings import warn

        cookie = self.__jsession_request()
        if not sessid:
            sessid = self.str_session
        if not scanid:
            scanid = self.str_scan
        if not fdir:
            fdir = self.__get_dicomdir(scanid)
        self.ensuredir(fdir)
        os.chdir(fdir)
        print('\n__download_files:  session %s, scan %s.\n' % (sessid, scanid))

        ddict = None
        for fname in fnames:
            ddict = get_datadict(cookie, sessid=sessid, scanid=scanid)
            for j, (name, path_dict) in enumerate(ddict.iteritems()):
                #print("downloading file %s to %s." % (name, fdir))
                if name == unicode(fname, 'utf-8'):
                    if os.access(path_dict['absolutePath'], os.R_OK):
                        self.__symlink(name, path_dict)
                    elif os.path.exists(name):
                        print("found file %s in %s." % (name, fdir))
                        path_dict['localPath'] = os.path.join(fdir, name)  # CHECK:  path_dict overwritten?  <JJL 2018-02-24>
                    else:
                        try:
                            with open(name, 'wb') as f:
                                r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                                for block in r.iter_content(1024):
                                    if not block:
                                        break
                                    f.write(block)
                        except IOError as e:
                            warn('fname must be a filename; dest must be a directory')
                            raise AssertionError(e.message)
                        path_dict['localPath'] = os.path.join(fdir, name) # CHECK:  path_dict overwritten?  <JJL 2018-02-24>

        self.__jsession_expire(cookie)
        return ddict

    def __download_legacy(self):
        """
        Is the legacy implementation from John Flavin's dcm2ni_wholeSession.py
        """
        import pydicom
        from warnings import warn
        cookie = self.__jsession_request()
        scanid_list = self.__get_scanid_list(cookie)

        for scanid in scanid_list:
            print('\nBeginning process for scan %s.' % scanid)
            skip_scan = False

            scan_resources = self.__get_scan_resources(cookie, scanid)
            dcm_resource_list = [res for res in scan_resources if res["label"] == "DICOM"]
            if len(dcm_resource_list) == 0:
                print("Scan %s has no DICOM resource. Skipping." % scanid)
                continue
            elif len(dcm_resource_list) > 1:
                print("Scan %s has more than one DICOM resource. Skipping." % scanid)
                continue
            dicom_resource = dcm_resource_list[0]
            if int(dicom_resource["file_count"]) == 0:
                print("DICOM resource for scan %s has no files. Skipping." % scanid)
                continue

            # download DICOMs
            print("Downloading files for scan %s." % scanid)
            dcmdict = self.__get_dicomdict(cookie, sessid=self.str_session, scanid=scanid)
            self.ensuredir(self.builddir)
            os.chdir(self.builddir)
            for j, (name, path_dict) in enumerate(dcmdict.iteritems()):
                skip_scan = False

                if os.access(path_dict['absolutePath'], os.R_OK):
                    self.__symlink(name, path_dict)
                else:
                    try:
                        with open(name, 'wb') as f:
                            r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                            if not r.ok:
                                print("Could not download file %s. Skipping scan %s." % (name, scanid))
                                skip_scan = True
                                continue  # break out of file download loop
                            for block in r.iter_content(1024):
                                if not block:
                                    break
                                f.write(block)
                        print('Downloaded file %s.' % name)
                    except IOError as e:
                        warn('fname must be a filename; dest must be a directory')
                        raise AssertionError(e.message)

                if j == 0 and not skip_scan:
                    dcm = pydicom.dcmread(name)
                    modality_header = dcm.get((0x0008, 0x0060), None)
                    if modality_header:
                        skip_scan = self.__check_skip_scan(name, modality_header)
                        if skip_scan:
                            print('Scan %s is a secondary capture. Skipping.' % scanid)
                            continue  # break out of file download loop
                    else:
                        print('Could not read modality from DICOM headers. Skipping.')
                        skip_scan = True
                        continue  # break out of file download loop

                path_dict['localPath'] = os.path.join(self.builddir, name)

            os.chdir(self.builddir)
            if skip_scan:
                continue # break out of the rest of the processing for scanid
            print('Done downloading scan %s.\n' % scanid)

        self.__jsession_expire(cookie)
        return

    def __check_skip_scan(self, name, modality_header):
        """
        For the first file in the list, we want to check its headers.
        If its modality indicates it is secondary, we don't want to convert the
        series and there is no reason to continue downloading the rest of the files.
        :name:
        :param modality_header:
        :return skip:
        """
        print('Checking modality in DICOM headers of file %s.' % name)
        print('Modality header: %s' % modality_header)
        modality = modality_header.value.strip("'").strip('"')
        skip = modality == 'SC' or modality == 'SR'
        return skip

    def __get_assessor(self, cookie):

        # get list of objects
        u = self.host + "/data/experiments/%s/assessors/ALL/resources/*freesurfer*/files?format=json" % self.str_session
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        adict = {obj['Name']: {'URI': self.host+obj['URI']} for obj in r.json()["ResultSet"]["Result"]}

        # have to manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/assessors/All/resources/*freesurfer*/files?format=json&locator=absolutePath" % self.str_session
        r = self.__get_url(u, headers=cookie, verify=False)
        for a in r.json()["ResultSet"]["Result"]:
            adict[a['Name']]['absolutePath'] = self.host+a['absolutePath']
        return adict

    def __get_dicom(self, dcm):
        """
        :param dcm:
        :return dcm_datset is a pydicom.dataset.FileDataset containing properties for DICOM fields:
        """
        from pydicom import dcmread
        try:
            dcm_datset = dcmread(dcm)
        except (AttributeError, TypeError):
            raise AssertionError('dcm must be a filename')
        return dcm_datset

    def __get_dicomdict(self, cookie, sessid=None, scanid=None):
        """
        :param cookie is from self.host+/data/JSESSION:
        :param sessid is str:
        :param scanid is str:
        :return ddict dictionary with 'Name', 'URI' from requests.json()["ResultSet"]["Result"]:
        """
        if not sessid:
            sessid = self.str_session
        if not scanid:
            raise AssertionError("self.__get_dicomdict has no scanid")

        # get list of DICOMs
        u = self.host + "/data/experiments/%s/scans/%s/resources/DICOM/files?format=json" % (sessid, scanid)
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        ddict = {dicom['Name']: {'URI': self.host+dicom['URI']}
                 for dicom in r.json()["ResultSet"]["Result"]}

        # John Flavin:  manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/scans/%s/resources/DICOM/files?format=json&locator=absolutePath" % (sessid, scanid)
        r = self.__get_url(u, headers=cookie, verify=False)
        for dcm in r.json()["ResultSet"]["Result"]:
            ddict[dcm['Name']]['absolutePath'] = self.host+dcm['absolutePath']
        return ddict

    def __get_dicomdir(self, scanid):
        if not scanid:
            return self.dir_session
        ddir = os.path.join(self.dir_SCANS, scanid)
        self.ensuredir(ddir)
        for f in os.listdir(ddir):
            os.remove(os.path.join(ddir, f))
        return ddir

    def __get_interfile(self, dcm):
        """
        :param dcm:
        :return lm_dict, a dictionary of interfile fields:
        """
        from interfile import Interfile
        try:
            lm_dict = Interfile.load(dcm)
        except (AttributeError, TypeError):
            raise AssertionError('dcm must be a filename')
        return lm_dict

    def __get_rawdatadict(self, cookie, sessid=None, scanid=None):
        """
        :param cookie is from self.host+/data/JSESSION:
        :param sessid is unused:
        :param scanid is unused:
        :return rddict with 'Name', 'URI' from requests.json()["ResultSet"]["Result"]:
        """

        # get list of DICOMs
        #print('__get_rawdatadict:  for session %s.' % self.str_session)
        u = self.host + "/data/experiments/%s/resources/RawData/files?format=json" % self.str_session
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        rddict = {rd['Name']: {'URI': self.host+rd['URI']} for rd in r.json()["ResultSet"]["Result"]}

        # have to manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/resources/RawData/files?format=json&locator=absolutePath" % self.str_session
        r = self.__get_url(u, headers=cookie, verify=False)
        for rd1 in r.json()["ResultSet"]["Result"]:
            rddict[rd1['Name']]['absolutePath'] = self.host+rd1['absolutePath']
        return rddict

    def __get_scan_resources(self, cookie, scanid):
        """
        is used by __download_legacy
        :param cookie:
        :param scanid:
        :return:
        """
        print("\n__get_scan_resources:  for scan %s.\n" % scanid)
        u = self.host + "/data/experiments/%s/scans/%s/resources?format=json" % (self.str_session, scanid)
        r = self.__get_url(u, headers=cookie, verify=False)
        resources = r.json()["ResultSet"]["Result"]
        #print('Found resources %s.' % ', '.join(res["label"] for res in resources))
        return resources

    def __get_scanid_list(self, cookie):
        """
        is used by __download_legacy
        :param cookie:
        :return:
        """
        print("\n__get_scanid_list:  for session ID %s.\n" % self.str_session)
        u = self.host + "/data/experiments/%s/scans?format=json" % self.str_session
        r = self.__get_url(u, headers=cookie, verify=False)
        sid_list = r.json()["ResultSet"]["Result"]
        idl = [scn['ID'] for scn in sid_list]
        #print('Found scans %s.' % ', '.join(idl))
        return idl

    def __get_url(self, url, **kwargs):
        import requests, sys
        try:
            r = requests.get(url, **kwargs)
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            raise AssertionError(e.message)
        if not r.ok:
            raise AssertionError("request.ok on %s was false" % url)
        return r

    def __is_imagetype3(self, dcm, itype3):
        import pydicom
        try:
            dataset = pydicom.dcmread(dcm)
        except (AttributeError, TypeError):
            raise AssertionError('dcm must be a filename')
        return dataset.ImageType == ['ORIGINAL', 'PRIMARY', itype3]

    def __jsession_request(self):
        r = self.__get_url(self.host + "/data/JSESSION", auth=(self.uid, self.pwd), verify=False)
        cookie = {"Cookie": "JSESSIONID=" + r.content}
        return cookie

    def __jsession_expire(self, cookie):
        import requests
        requests.delete(self.host + "/data/JSESSION", headers=cookie, verify=False)
        return

    def __resources_available(self):
        return True

    def __select_bfiles(self, bfs):
        """
        examines rawdata dcms and selects bf for norm and listmode data
        :param bfs:
        :return bf:
        """
        bf = []
        for b in bfs:
            if self.is_norm(self.filename2dcm(b)) or self.is_listmode(self.filename2dcm(b)):
                bf.append(b)
        return bf

    def __select_tracer(self, dcms, tracer='Fluorodeoxyglucose'):
        """
        examines rawdata dcms for given tracer and selects bf for norm and listmode data
        :param dcms:
        :param tracer in ['Fluorodeoxyglucose', 'Oxygen-water', 'Oxygen', 'Carbon']:
        :return bf:
        """
        bf = []
        for d in dcms:
            if self.is_tracer(d, tracer):
                bf.append(self.filename2bf(d))
        return bf

    def __symlink(self, name, path_dict):
        from shutil import copy as fileCopy
        try:
            os.symlink(path_dict['absolutePath'], name)
            print('Made link to %s.' % path_dict['absolutePath'])
        except:
            fileCopy(path_dict['absolutePath'], name)
            print('Copied %s.' % path_dict['absolutePath'])
        return

    def __wait(self):
        import time
        time.sleep(self.sleep_duration)
        return

    def __init__(self, uid, pwd, prefix="/work/SubjectsStash", prj="CCIR_00754", sbj="HYGLY48", ses="CNDA_E249152", scn="1"):
        """
        :param uid:
        :param pwd:
        :param prj:
        :param sbj:
        :param ses:
        :param scn:
        :param prefix is the preferred cache directory:
        """
        self.host     = 'https://cnda.wustl.edu'
        self.uid      = uid #os.getenv('CNDA_UID')
        self.pwd      = pwd #os.getenv('CNDA_PWD')
        self.builddir = prefix
        os.chdir(self.builddir)
        self.xnat     = pyxnat.Interface(self.host, user=self.uid, password=self.pwd, cachedir=self.builddir)
        self.project  = self.xnat.select.project(prj)
        self.subject  = self.project.subject(sbj)
        self.session  = self.subject.experiment(ses)
        self.scan     = self.session.scan(scn)


if __name__ == '__main__':
    import argparse
    from argparse import RawDescriptionHelpFormatter
    p = argparse.ArgumentParser(
        description=
        "xnatpet stages data from XNAT server to local filesystem; \n"
        "e.g.:  python xnatpet.py -p /path/to/projects -j PROJECT_ID \\\n"
        "       -c [('xnat:petSessionData/DATE', '>', '2018-01-01'), 'AND']",
        formatter_class=RawDescriptionHelpFormatter)
    p.add_argument('-p', '--prefix',
                   metavar='<path>',
                   required=True,
                   help='path containing project-level data')
    p.add_argument('-j', '--proj',
                   metavar='<ID>',
                   required=True,
                   help='project ID as known by XNAT')
    p.add_argument('-c', '--constraints',
                   metavar="[('<param>', '<logical>', '<value>'), '<LOGICAL>']",
                   default=None,
                   required=True,
                   help='must express the constraint API of pyxnat;'
                        'see also https://groups.google.com/forum/#!topic/xnat_discussion/SHWAxHNb570')
    args = p.parse_args()
    r = StageXnat(os.getenv('CNDA_UID'), os.getenv('CNDA_PWD'), prefix=args.prefix, prj=args.proj)
    r.stage_project(args.constraints)