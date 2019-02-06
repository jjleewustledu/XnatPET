import pyxnat

class StageXnat(object):
    """Uses pyxnat or requests packages to interact with an XNAT REST API to download data from
       projects, subjects, sessions/experiments, scans, rawdata-resources and freesurfer-assessors."""

    __author__ = "John J. Lee"
    __copyright__ = "Copyright 2019"
    sleep_duration = 600 # secs
    tracers = ['Fluorodeoxyglucose', 'Carbon', 'Oxygen', 'Oxygen-water']



    def stage_project(self):
        for s in self.fetch_subjects():
            self.stage_subject(s)
        return

    def stage_subject(self, sbj):
        for s in self.fetch_sessions(sbj):
            self.stage_session(s)
        return

    def stage_session(self, ses):
        while self.on_schedule() and not self.__resources_available():
            self.__wait()
        for s in self.fetch_scans(ses):
            self.stage_scan(s)
        for t in self.tracers:
            self.stage_rawdata(ses, t)
        return

    def stage_scan(self, scn, ses=None, sdir=None):
        if not ses:
            ses = self.session
        if not sdir:
            sdir = self.builddir
        self.stage_dicoms(scn, ses=ses, ddir=sdir)
        return

    def stage_ct(self, sbj):
        import os
        for s in self.fetch_sessions(sbj):
            if self.session_has_ct(s):
                ctdir = os.path.join(self.builddir, 'ct')
                self.ensuredir(ctdir)
                self.stage_scan(s.scans('2'), ses=s, sdir=ctdir)
                return
        raise AssertionError("stage_ct could not find a ct sessions for %s" % sbj.get())

    def stage_rawdata(self, ses, tracer='Fluorodeoxyglucose'):
        """
        downloads session rawdata as .bf files
        :param ses is a pyxnat session (a.k.a., experiment):
        :param tracer in ['Fluorodeoxyglucose', 'Oxygen-water', 'Oxygen', 'Carbon']:
        :return dests := list of downloaded rawdata in final destinations
        """
        while self.on_schedule() and not self.__resources_available():
            self.__wait()
        ds = self.stage_dicoms_rawdata(ses)
        bs = self.stage_bfiles_rawdata(ses, ds, tracer) # all .dcm -> .bf
        dests = []
        for b in bs:
            print('\nstage_rawdata:  moving %s\n' % b)
            dests.append(self.move_rawdata(self.filename2bf(b), tracer))
            dests.append(self.move_rawdata(self.filename2dcm(b), tracer)) # .dcm has information needed by move_rawdata
        return dests

    def stage_dicoms(self, scn, ses=None, fs='*.dcm', ddir=None):
        if not ses:
            ses = self.session
        ds = scn.resources().files(fs).get()
        self.__download_ct(ds, self.__get_dicomdict, sessid=ses._urn, scanid=scn.get()[0], fdir=ddir)
        return ds

    def stage_dicoms_rawdata(self, ses, the_files='*.dcm'):
        """
        downloads .dcm files from the session resources tagged RawData
        :param ses is a pyxnat session (a.k.a., experiment):
        :param the_files is a string specifier for requests from ses:
        :return ds is the list of downloaded DICOMs:
        """
        ds = ses.resources().files(the_files).get()
        self.__download_files(ds, self.__get_rawdatadict, fdir=self.builddir)
        return ds

    def stage_bfiles_rawdata(self, ses, the_files='*.dcm', tracer='Fluorodeoxyglucose'):
        """
        downloads .bf files from the session resources tagged RawData
        :param ses is a pxnat session (a.k.a., experiment):
        :param the_files is a string specifier for requests from sess or a list of specifiers or a list of files:
        :param tracer:
        :return bs is the list of downloaded .bf files:
        """
        if not the_files:
            return False
        ds = []
        if isinstance(the_files, str):
            ds = ses.resources().files(the_files).get() # expands specifier the_files
        if isinstance(the_files, list):
            for f in the_files:
                ds.append(ses.resources().files(f).get()) # expands f as needed
            ds = [item for sublist in ds for item in sublist] # flattens list of lists
            # From Alex Martelli
            # https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-list-of-lists?page=1&tab=votes#tab-top

        bs = self.__select_tracer(ds, tracer)
        bs = self.__select_bfiles(bs)
        self.__download_files(bs, self.__get_rawdatadict, fdir=self.builddir)
        return bs

    def stage_freesurfer(self, ses):
        """
        downloads assessors labelled freesurfer from a session
        :param ses:
        :return:
        """
        self.__download_assessor()
        return

    def stage_umaps(self, ses, umap_desc=u'Head_MRAC_Brain_HiRes_in_UMAP'):
        """
        downloads .dcm files for all umaps from a session, saving to a folder named self.umap_desc
        :param ses is a pyxnat session (a.k.a., experiment):
        :param umap_desc is a pydicom SeriesDescription:
        :return upaths is a list of umap path names:
        """
        import pydicom
        from os import path
        from warnings import warn
        upaths = []
        scans = ses.scans('*')
        scansg = scans.get()
        isc = 0
        for s in scans:
            ds = s.resources().files('*.dcm').get()
            try:
                self.__download_files([ds[0]], self.__get_dicomdict, scanid=scansg[isc])
                dinfo = pydicom.dcmread(path.join(scansg[isc], ds[0]))
                if umap_desc == dinfo.SeriesDescription:
                    self.__download_scan(self.__get_dicomdict, scanid=scansg[isc])
                    upaths.append(
                        self.move_scan(scansg[isc], scaninfo=dinfo))
            except IOError as e:
                warn(e.message)
            isc += 1
        return upaths



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
        provides best estimate of end time (GMT) of MR sequences
        :param dcm:
        :return:
        """
        d = self.__get_dicom(dcm)
        return d.SeriesTime # hhmmss.ffffff after http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html

    def dcm_studytime(self, dcm):
        """
        provides best estimate of start time (GMT) of listmode collection
        :param dcm filename:
        :return:
        """
        d = self.__get_dicom(dcm)
        return d.StudyTime # hhmmss.ffffff after http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html

    def ensuredir(self, d):
        import os
        try:
            if not os.path.exists(d):
                os.mkdir(d)
        except IOError as e:
            raise AssertionError(e.message)
        else:
            return d

    def fetch_subjects(self, prj=None):
        if not prj:
            prj = self.project
        return prj.subjects('*')

    def fetch_sessions(self, sbj=None):
        if not sbj:
            sbj = self.subject
        return sbj.experiments('*')

    def fetch_scans(self, ses=None):
        if not ses:
            ses = self.session
        return ses.scans('*')

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

    def move_rawdata(self, b, tracer):
        import os
        from os import path
        import shutil
        tdir = self.rawdata_dir(b, tracer)
        self.ensuredir(tdir)
        bdest = path.join(tdir, path.basename(b))
        shutil.move(b, bdest)
        return bdest

    def move_scan(self, spath0, scaninfo):
        """
        moves .dcm from a scan (:= scaninfo) to spath (:= scaninfo)
        :param spath0 is a path containing .dcm:
        :param scaninfo := pydicom.dcmread():
        :return spath:
        """
        import os
        from os import path
        import shutil
        spath = path.join(self.builddir,
                          str(scaninfo.SeriesDescription) + '_DT' +
                          str(scaninfo.SeriesDate) +
                          str(scaninfo.AcquisitionTime))
        shutil.move(spath0, spath)
        return spath

    def on_schedule(self):
        return True

    def rawdata_dir(self, b, tracer):
        import os
        tdir = os.path.join(
            self.builddir,
            self.tracer_label(tracer, b) + '_' + self.visit_label(b) + '-Converted-NAC')
        return tdir

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
        return 'DT' + d.StudyDate + d.StudyTime # str DTYYYYMMDDhhmmss.xxxxxx




    # CLASS-PRIVATE #########################################################################

    def __download_assessor(self):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :return filesystem with assessors unpacked to self.builddir && symlink to freesurfer mri path
        """
        import os
        from shutil import copyfileobj
        from warnings import warn
        from zipfile import ZipFile
        from glob2 import glob

        cookie = self.__jsession_request()
        print("\nDownloading assessors for session %s." % self.session.get()[0])
        uri = self.host + "/data/experiments/%s/assessors/ALL/files?format=zip" % self.session.get()[0]
        zip = "assessors_ALL_files.zip"

        try:
            os.chdir(self.builddir)
            with open(zip, 'wb') as f:
                r = self.__get_url(uri, headers=cookie, verify=False, stream=True)
                copyfileobj(r.raw, f)
            z = ZipFile(zip, 'r')
            z.extractall(self.builddir)
            z.close()
            os.remove(zip)
            p = glob(os.path.join('CNDA*freesurfer*', 'out', 'resources', 'DATA', 'files', '*', 'mri'))
            os.symlink(p[0], 'mri')
        except IOError as e:
            raise AssertionError(e.message)

        self.__jsession_expire(cookie)
        print('Done downloading assessors for %s.\n' % self.session.get()[0])
        return

    def __download_ct(self, fnames, get_datadict, sessid=None, scanid=None, fdir=None):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :param fnames are file names:
        :param get_datadict is a function that returns fdict and fdir:
        :param sessid is str:
        :param scanid is str:
        :param fdir is a filesystem path:
        """
        import os
        from warnings import warn

        cookie = self.__jsession_request()
        if not sessid:
            sessid = self.session.get()[0]
        if not scanid:
            scanid = self.scan.get()[0]
        if not fdir:
            fdir = self.__get_dicomdir(scanid)
        os.chdir(fdir)
        print('\nBeginning process for session %s, scan %s.' % (sessid, scanid))
        fdict = get_datadict(cookie, sessid=sessid, scanid=scanid)
        for j, (name, path_dict) in enumerate(fdict.iteritems()):

            print("Downloading file %s to %s." % (name, fdir))
            try:
                with open(name, 'wb') as f:
                    r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                    for block in r.iter_content(1024):
                        if not block:
                            break
                        f.write(block)
                print('Downloaded file %s.' % name)
            except IOError as e:
                warn('fname must be a filename; dest must be a directory')
                raise AssertionError(e.message)

        os.chdir(self.builddir)
        self.__jsession_expire(cookie)
        return

    def __download_files(self, fnames, get_datadict, sessid=None, scanid=None, fdir=None):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :param fnames are file names:
        :param get_datadict is a function that returns fdict and fdir:
        :param sessid is str:
        :param scanid is str:
        :param fdir is a filesystem path:
        """
        import os
        from warnings import warn

        cookie = self.__jsession_request()
        if not sessid:
            sessid = self.session.get()[0]
        if not scanid:
            scanid = self.scan.get()[0]
        if not fdir:
            fdir = self.__get_dicomdir(scanid)
        os.chdir(fdir)
        print('\nBeginning process for session %s, scan %s.' % (sessid, scanid))

        for fname in fnames:

            print("Downloading file %s to %s." % (fname, fdir))
            fdict = get_datadict(cookie, sessid=sessid, scanid=scanid)
            for j, (name, path_dict) in enumerate(fdict.iteritems()):

                if name == unicode(fname, 'utf-8'):
                    if os.access(path_dict['absolutePath'], os.R_OK):
                        self.__symlink(name, path_dict)
                    else:
                        try:
                            with open(name, 'wb') as f:
                                r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                                for block in r.iter_content(1024):
                                    if not block:
                                        break
                                    f.write(block)
                            print('Downloaded file %s.' % name)
                        except IOError as e:
                            warn('fname must be a filename; dest must be a directory')
                            raise AssertionError(e.message)
                    path_dict['localPath'] = os.path.join(fdir, name)

            os.chdir(self.builddir)
            print('Done downloading %s.\n' % fname)

        self.__jsession_expire(cookie)
        return

    def __download_legacy(self):
        """
        Is the legacy implementation from John Flavin's dcm2ni_wholeSession.py
        """
        import pydicom
        import os
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
            dcmdict = self.__get_dicomdict(cookie, sessid=self.session.get()[0], scanid=scanid)
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

    def __download_scan(self, get_datadict, sessid=None, scanid=None, fdir=None):
        """
        See also John Flavin's dcm2ni_wholeSession.py
        :param get_datadict is a function that returns fdict and fdir:
        :param sessid is str:
        :param scanid is str:
        :param fdir is a filesystem path:
        """
        import os
        import pydicom
        from warnings import warn

        cookie = self.__jsession_request()
        if not sessid:
            sessid = self.session.get()[0]
        if not scanid:
            scanid = self.scan.get()[0]
        if not fdir:
            fdir = self.__get_dicomdir(scanid)
        os.chdir(fdir)
        print('\nBeginning process for scan %s.' % scanid)
        scan_resources = self.__get_scan_resources(cookie, scanid)
        dcm_resource_list = [res for res in scan_resources if res["label"] == "DICOM"]
        if len(dcm_resource_list) == 0:
            print("Scan %s has no DICOM resource. Skipping." % scanid)
            return
        elif len(dcm_resource_list) > 1:
            print("Scan %s has more than one DICOM resource. Skipping." % scanid)
            return
        dicom_resource = dcm_resource_list[0]
        if int(dicom_resource["file_count"]) == 0:
            print("DICOM resource for scan %s has no files. Skipping." % scanid)
            return
        print("Downloading scan %s." % scanid)

        fdict = get_datadict(cookie, sessid=sessid, scanid=scanid)
        for j, (name, path_dict) in enumerate(fdict.iteritems()):
            skip_scan = False

            print("Downloading %s." % name)
            if os.access(path_dict['absolutePath'], os.R_OK):
                self.__symlink(name, path_dict)
            else:
                try:
                     with open(name, 'wb') as f:
                         r = self.__get_url(path_dict['URI'], headers=cookie, verify=False, stream=True)
                         for block in r.iter_content(1024):
                             if not block:
                                 return
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
                        return
                else:
                    print('Could not read modality from DICOM headers. Skipping.')
                    skip_scan = True
                    return

            path_dict['localPath'] = os.path.join(fdir, name)
            if skip_scan:
                return
            print('Done downloading %s.\n' % name)

        os.chdir(self.builddir)
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
        u = self.host + "/data/experiments/%s/assessors/ALL/resources/*freesurfer*/files?format=json" % self.session.get()[0]
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        adict = {obj['Name']: {'URI': self.host+obj['URI']} for obj in r.json()["ResultSet"]["Result"]}

        # have to manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/assessors/All/resources/*freesurfer*/files?format=json&locator=absolutePath" % self.session.get()[0]
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
            sessid = self.session.get()[0]
        if not scanid:
            raise AssertionError("self.__get_dicomdict has no scanid")

        # get list of DICOMs
        print('Get list of DICOM files for scan %s.' % scanid)
        u = self.host + "/data/experiments/%s/scans/%s/resources/DICOM/files?format=json" % (sessid, scanid)
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        ddict = {dicom['Name']: {'URI': self.host+dicom['URI']} for dicom in r.json()["ResultSet"]["Result"]}

        # have to manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/scans/%s/resources/DICOM/files?format=json&locator=absolutePath" % (
            sessid, scanid)
        r = self.__get_url(u, headers=cookie, verify=False)
        for dcm in r.json()["ResultSet"]["Result"]:
            ddict[dcm['Name']]['absolutePath'] = self.host+dcm['absolutePath']
        return ddict

    def __get_dicomdir(self, scanid):
        import os
        if not scanid:
            return self.builddir
        ddir = os.path.join(self.builddir, scanid)
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
        print('Get list of RawData files for session %s.' % self.session.get()[0])
        u = self.host + "/data/experiments/%s/resources/RawData/files?format=json" % self.session.get()[0]
        r = self.__get_url(u, headers=cookie, verify=False)

        # John Flavin:  "I don't like the results being in a list, so I will build a dict keyed off file name"
        rddict = {rd['Name']: {'URI': self.host+rd['URI']} for rd in r.json()["ResultSet"]["Result"]}

        # have to manually add absolutePath with a separate request
        u = self.host + "/data/experiments/%s/resources/RawData/files?format=json&locator=absolutePath" % self.session.get()[0]
        r = self.__get_url(u, headers=cookie, verify=False)
        for rd1 in r.json()["ResultSet"]["Result"]:
            rddict[rd1['Name']]['absolutePath'] = self.host+rd1['absolutePath']
        return rddict

    def __get_scan_resources(self, cookie, scanid):
        print("Get scan resources for scan %s." % scanid)
        u = self.host + "/data/experiments/%s/scans/%s/resources?format=json" % (self.session.get()[0], scanid)
        r = self.__get_url(u, headers=cookie, verify=False)
        resources = r.json()["ResultSet"]["Result"]
        print('Found resources %s.' % ', '.join(res["label"] for res in resources))
        return resources

    def __get_scanid_list(self, cookie):
        print("Get scan list for session ID %s." % self.session.get()[0])
        u = self.host + "/data/experiments/%s/scans?format=json" % self.session.get()[0]
        r = self.__get_url(u, headers=cookie, verify=False)
        request_result_list = r.json()["ResultSet"]["Result"]
        idl = [scan['ID'] for scan in request_result_list]
        print('Found scans %s.' % ', '.join(idl))
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
        import os
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

    def __init__(self, uid, pwd, prj="CCIR_00754", sbj="HYGLY48", ses="CNDA_E249152", scn="*", cch="/work/SubjectsStash"):
        """
        :param uid:
        :param pwd:
        :param prj:
        :param sbj:
        :param ses:
        :param scn:
        :param cch is the preferred cache directory:
        """
        import os
        self.host     = 'https://cnda.wustl.edu'
        self.uid      = uid
        self.pwd      = pwd
        self.builddir = cch
        self.xnat     = pyxnat.Interface(self.host, user=self.uid, password=self.pwd, cachedir=self.builddir)
        self.project  = self.xnat.select.project(prj)
        self.subject  = self.project.subject(sbj)
        self.session  = self.subject.experiments(ses)
        self.scan     = self.session.scan(scn)
