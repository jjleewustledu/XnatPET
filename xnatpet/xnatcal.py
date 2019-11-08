import os
import errno
import pyxnat
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime
from warnings import warn

class Calibration(object):
    """Calibrates PET stored on XNAT server"""

    __author__ = "John J. Lee"
    __copyright__ = "Copyright 2019"

    calibration_duration = 900 # sec
    daterange = [datetime(2016, 7, 18, 0, 0, 0, 0), datetime.now()]
    max_calibration_filesize = 1e9 # bytes
    project = None
    tracers = ['FDG']
    use_only_cachedir = True



    def create_tracerloc_list(self):
        """containing calibration listmode, norm data"""

        elist = []
        if self.use_only_cachedir:
            for e in self.select_experiments():
                for t in self.select_tracers(e):
                    for d in self.select_dates(t):
                        if self.consistent_duration(d): # and self.consistent_filesize(d):
                            elist.append(d)
        else:
            raise NotImplementedError
        return elist

    def create_NAC(self):
        return None

    def create_AC(self):
        return None

    def stage_rawdata(self):
        return

    def stage_umaps(self):
        return



    def select_experiments(self):
        """
        :return experiment locations as list:
        """
        selection = []
        listprj = os.listdir(self.prjdir)
        for l in listprj:
            if "ses-" in l:
                selection.append(os.path.join(self.prjdir, l))
        return selection

    def select_tracers(self, exp):
        """
        :param exp is experiment location
        :return tracer locations, consistent with calibration, as list:
        """
        assert(os.path.exists(exp))
        listtra = []
        for t in self.tracers:
            for l in self.tracer_locations(exp, t):
                listtra.append(l)
        return listtra

    def select_dates(self, traloc):
        """
        :param traloc as list:
        :return tracer locations, consistent with calibration dates, as list:
        """
        assert(os.path.exists(traloc))
        if isinstance(traloc, basestring):
            if self.consistent_date(traloc):
                return [traloc]
            else:
                return []
        try:
            listtra = []
            for t in traloc:
                if self.consistent_date(t):
                    listtra.append(t)
            return listtra
        except TypeError:
            return []

    def bf_for_calibration(self, dcmloc):
        """
        :param dcmloc filenamne:
        :return bf filename:
        """
        return os.path.splitext(dcmloc)[0] + '.bf'

    def consistent_date(self, traloc):
        import re
        p = re.compile("\w+_DT(\d+).(\d+)\w*")
        trafld = os.path.basename(traloc)
        result = p.search(trafld)
        dt = datetime.strptime(result.group(1), '%Y%m%d%H%M%S')
        return self.daterange[0] <= dt and dt <= self.daterange[1]

    def consistent_duration(self, traloc):
        dcm = self.dcm_for_calibration(traloc)
        try:
            dur = self.ifh_imageduration(dcm)
            if not dur:
                dur = self.dcm2duration(dcm)
        except TypeError:
            dur = self.dcm2duration(dcm)
        assert(self.isnumeric(dur))
        return dur < self.calibration_duration

    def consistent_filesize(self, traloc):
        bf = self.bf_for_calibration(
            self.dcm_for_calibration(traloc))
        return self.size_of_bf(bf) < self.max_calibration_filesize



    # UTITILIES ########################################################

    def bin2str(self, stream):
        """https://stackoverflow.com/questions/6804582/extract-strings-from-a-binary-file-in-python"""
        import re
        chars = r"A-Za-z0-9/\-:.,_$%'()[\]<>= "
        shortest_run = 4
        regexp = '[%s]{%d,}' % (chars, shortest_run)
        pattern = re.compile(regexp)
        data = stream.read()
        return pattern.findall(data)

    def dcm_for_calibration(self, traloc):
        """
        :param traloc is the tracer location:
        :return dcm filename:
        """
        from glob2 import glob
        dcms = glob(os.path.join(traloc, 'LM', '*.dcm'))
        return dcms[-1] # non-last elements may have been aborted early

    def dcm2duration0(self, dcm):
        import re
        dcmobj = self.__get_dicom(dcm)
        pattern = re.compile(u"MRAC_PET_(\d+)min")
        result = pattern.search(dcmob.SeriesDescription)
        return int(result.group(1))

    def dcm2duration(self, dcm):
        """https://stackoverflow.com/questions/7852855/in-python-how-do-you-convert-a-datetime-object-to-seconds"""
        from datetime import datetime
        dcmobj = self.__get_dicom(dcm)
        t1 = datetime.strptime(dcmobj.InstanceCreationTime, '%H%M%S.%f')
        t0 = datetime.strptime(dcmobj.AcquisitionTime, '%H%M%S.%f')
        return (t1 - t0).total_seconds()

    def get_interfile(self, dcm):
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

    def ifh_imageduration(self, dcm):
        from interfile import Interfile
        try:
            lm_dict = self.get_interfile(dcm)
            return int(lm_dict['image duration']['value'])  # sec
        except Interfile.ParsingError:
            return self.search_image_duration_value(dcm)

    def isnumeric(self, x):
        # https://stackoverflow.com/questions/4187185/how-can-i-check-if-my-python-object-is-a-number
        import numbers
        import decimal
        return bool([isinstance(x, numbers.Number) for x in (0, 0.0, 0j, decimal.Decimal(0))])

    def search_image_duration_value(self, dcm):
        import re
        p = re.compile("image duration \(sec\) :=(\d+)")
        d = open(dcm, mode='rb')
        string = self.bin2str(d)
        result = p.search(string)
        assert(result.group(1))
        return int(result.group(1))

    def size_of_bf(self, fn):
        """
        :param fileprefix with any single extension:
        :return size of bf file in bytes:
        """
        sinfo = os.stat(os.path.splitext(fn)[0] + '.bf')
        return sinfo.st_size

    def tracer_locations(self, exploc, tracer):
        from glob2 import glob
        assert (os.path.exists(exploc))
        return glob(os.path.join(exploc, tracer.upper() + '_DT*.*-Converted-*AC'))

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



    def __init__(self, user, password, cachedir="/scratch/jjlee/Singularity", prj="CCIR_00754"):
        """
        :param user:
        :param password:
        :param cachedir is the preferred cache directory:
        :param prj:
        """
        self.host     = 'https://cnda.wustl.edu'
        self.user     = user #os.getenv('CNDA_UID')
        self.password = password #os.getenv('CNDA_PWD')
        self.cachedir = cachedir
        self.prjdir   = os.path.join(self.cachedir, prj)
        os.chdir(self.cachedir)
        #self.xnat     = pyxnat.Interface(self.host, user=self.user, password=self.password, cachedir=self.cachedir)
        #assert(isinstance(self.xnat, pyxnat.core.interfaces.Interface))
        #self.project  = self.xnat.select.project(prj)
        #assert(isinstance(self.project, pyxnat.core.resources.Project))




def main():
    from xnatpet.xnatcal import Calibration
    import argparse, textwrap
    import os

    p = argparse.ArgumentParser(
        description='Calibrates PET stored on XNAT server',
        usage=textwrap.dedent('''\

    python xnatcal.py -h
    nvidia-docker run -it \\
                  -v ${DOCKER_HOME}/hardwareumaps/:/hardwareumaps \\
                  -v ${SINGULARITY_HOME}/:/SubjectsDir \\
                  niftycal-image:test -h
    singularity exec \\
                --nv \\
                --bind $SINGULARITY_HOME/hardwareumaps:/hardwareumaps \\
                --bind $SINGULARITY_HOME:/SubjectsDir \\
                $SINGULARITY_HOME/niftycal-image_test.sif \\
                "python" "/work/NiftyCal/xnatpet/xnatcal.py" "-h" 
        '''),
        formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('-m', '--method',
                   metavar='create_tracerloc_list|create_NAC|create_AC',
                   type=str,
                   default='create_tracerloc_list')
    p.add_argument('-c', '--cachedir',
                   metavar='/path/to/cachedir',
                   help='location containing projects',
                   type=str,
                   required=True)
    p.add_argument('-p', '--project',
                   metavar='CCIR_00754',
                   type=str,
                   default='CCIR_00754')
    args = p.parse_args()

    c = Calibration(os.getenv('CNDA_UID'), os.getenv('CNDA_PWD'), cachedir=args.cachedir, prj=args.project)
    if args.method.lower() == 'create_ac':
        print('main.args.method->create_AC')
        c.create_AC()
    elif args.method.lower() == 'create_nac':
        print('main.args.method->create_NAC')
        c.create_NAC()
    else:
        print('main.args.method->create_tracerloc_list')
        c.create_tracerloc_list()

if __name__ == '__main__':
    main()