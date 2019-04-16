import argparse, requests, os, sys
import dicom as dicomLib
# from shutil import copy as fileCopy
from nipype.interfaces.dcm2nii import Dcm2nii

def cleanServer(server):
    server.strip()
    if (server[-1] == '/'):
        server = server[:-1]
    if (server.find('http') == -1):
        server = 'https://' + server
    return server

def get(url,**kwargs):
    try:
        r = requests.get( url, **kwargs )
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        print "Request Failed"
        print "    " + str( e )
        sys.exit(1)
    return r

def isTrue(arg):
    return arg is not None and (arg=='Y' or arg=='1' or arg=='True')


parser = argparse.ArgumentParser(description="Run dcm2nii on every file in a session")
parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--session", help="Session ID", required=True)
parser.add_argument("--cachedir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--nii", help="Create .nii file, or .img/.hdr pair")
parser.add_argument("--gzip", help="GZip .nii output into .nii.gz?")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args = parser.parse_args()
auth = (args.user,args.password)
host = cleanServer(args.host)
session = args.session
overwrite = isTrue(args.overwrite)
makenii = isTrue(args.nii)
gzip = isTrue(args.gzip)
dicomdir = args.dicomdir
niftidir = args.niftidir

builddir = os.getcwd()

# Set up working directory
if not os.access(dicomdir, os.R_OK):
    print 'Making DICOM directory %s' % dicomdir
    os.mkdir(dicomdir)
if not os.access(niftidir, os.R_OK):
    print 'Making NIFTI directory %s' % niftidir
    os.mkdir(niftidir)


# Get JSESSION token
r = get( host+"/data/JSESSION", auth=auth, verify=False )
jsessionID = r.content
print "JSESSION ID: %s" % jsessionID
cookie = {"Cookie": "JSESSIONID=" + jsessionID}

# Get list of scan ids
print "Get scan list for session ID %s." % session
r = get( host+"/data/experiments/%s/scans?format=json"%session, headers=cookie, verify=False )
scanRequestResultList = r.json()["ResultSet"]["Result"]
scanIDList = [scan['ID'] for scan in scanRequestResultList]
print 'Found scans %s.'%', '.join(scanIDList)

for scanid in scanIDList:
    print
    print 'Beginning process for scan %s.'%scanid

    # Get scan resources
    print "Get scan resources for scan %s." % scanid
    r = get( host+"/data/experiments/%s/scans/%s/resources?format=json"%(session,scanid), headers=cookie, verify=False )
    scanResources = r.json()["ResultSet"]["Result"]
    print 'Found resources %s.'%', '.join(res["label"] for res in scanResources)

    ##########
    # Do initial checks to determine if scan should be skipped
    hasNifti = any([res["label"]=="NIFTI" for res in scanResources]) # Store this for later
    if hasNifti and not overwrite:
        print "Scan %s has a preexisting NIFTI resource, and I am running with overwrite=False. Skipping." % scanid
        continue

    dicomResourceList = [res for res in scanResources if res["label"]=="DICOM"]
    if len(dicomResourceList) == 0:
        print "Scan %s has no DICOM resource. Skipping." % scanid
        # scanInfo['hasDicom'] = False
        continue
    elif len(dicomResourceList) > 1:
        print "Scan %s has more than one DICOM resource. Skipping." % scanid
        # scanInfo['hasDicom'] = False
        continue

    dicomResource = dicomResourceList[0]
    if int(dicomResource["file_count"]) == 0:
        print "DICOM resource for scan %s has no files. Skipping." % scanid
        # scanInfo['hasDicom'] = True
        continue

    ##########
    # Prepare DICOM directory structure
    print
    scanDicomDir = os.path.join(dicomdir,scanid)
    if not os.access(scanDicomDir, os.R_OK):
        print 'Making scan DICOM directory %s.' % scanDicomDir
        os.mkdir(scanDicomDir)
    # Remove any existing files in the cachedir.
    # This is unlikely to happen in any environment other than testing.
    for f in os.listdir(scanDicomDir):
        os.remove(os.path.join(scanDicomDir,f))

    ##########
    # Get list of DICOMs
    print 'Get list of DICOM files for scan %s.' % scanid
    r = get( host+"/data/experiments/%s/scans/%s/resources/DICOM/files?format=json"%(session,scanid), headers=cookie, verify=False )
    # I don't like the results being in a list, so I will build a dict keyed off file name
    dicomFileDict = {dicom['Name']: {'URI':dicom['URI']} for dicom in r.json()["ResultSet"]["Result"]}

    # Have to manually add absolutePath with a separate request
    r = get( host+"/data/experiments/%s/scans/%s/resources/DICOM/files?format=json&locator=absolutePath"%(session,scanid),
        headers=cookie, verify=False )
    for dicom in r.json()["ResultSet"]["Result"]:
        dicomFileDict[dicom['Name']]['absolutePath'] = dicom['absolutePath']

    ##########
    # Download DICOMs
    print "Downloading files for scan %s." % scanid
    os.chdir(scanDicomDir)
    for j,(name,pathDict) in enumerate(dicomFileDict.iteritems()):
        skipScan = False

        if os.access(pathDict['absolutePath'], os.R_OK):
            try:
                os.symlink(pathDict['absolutePath'],name)
                print 'Made link to %s.' % pathDict['absolutePath']
            except:
                fileCopy(pathDict['absolutePath'],name)
                print 'Copied %s.' % pathDict['absolutePath']
        else:
            with open(name, 'wb') as f:
                r = get(pathDict['URI'], headers=cookie, verify=False, stream=True)

                if not r.ok:
                    print "Could not download file %s. Skipping scan %s." % (name,scanid)
                    skipScan = True
                    continue # break out of file download loop

                for block in r.iter_content(1024):
                    if not block:
                        break

                    f.write(block)
            print 'Downloaded file %s.' % name

        if j==0 and not skipScan:
            # For the first file in the list, we want to check its headers.
            # If its modality indicates it is secondary, we don't want to convert the
            # series and there is no reason to continue downloading the rest of the files.
            print 'Checking modality in DICOM headers of file %s.'%name
            d = dicomLib.read_file(name)
            modalityHeader = d.get((0x0008,0x0060), None)
            if modalityHeader:
                print 'Modality header: %s'%modalityHeader
                modality = modalityHeader.value.strip("'").strip('"')
                skipScan = modality == 'SC' or modality == 'SR'
                if skipScan:
                    print 'Scan %s is a secondary capture. Skipping.' % scanid
                    continue # break out of file download loop
            else:
                print 'Could not read modality from DICOM headers. Skipping.'
                skipScan = True
                continue # break out of file download loop

        pathDict['localPath'] = os.path.join(scanDicomDir,name)
    os.chdir(builddir)

    if skipScan:
        # break out of the rest of the processing for scanid
        continue

    print 'Done downloading for scan %s.'%scanid
    print


    ##########
    # Prepare NIFTI directory structure
    scanNiftiDir = os.path.join(niftidir,scanid)
    if not os.access(scanNiftiDir, os.R_OK):
        print 'Creating scan NIFTI directory %s.' % scanNiftiDir
        os.mkdir(scanNiftiDir)
    # Remove any existing files in the cachedir.
    # This is unlikely to happen in any environment other than testing.
    for f in os.listdir(scanNiftiDir):
        os.remove(os.path.join(scanNiftiDir,f))

    ##########
    # Prepare and run Dcm2nii nipype interface
    converter = Dcm2nii()
    converter.inputs.source_names = [pathDict['localPath'] for pathDict in dicomFileDict.itervalues()]
    converter.inputs.nii_output = makenii
    converter.inputs.gzip_output = gzip
    converter.inputs.output_dir = scanNiftiDir
    converter.inputs.reorient = False
    converter.inputs.reorient_and_crop = False

    print 'Converting scan %s to NIFTI...' % scanid
    print converter.cmdline
    result = converter.run()
    print 'Done.'

    outfiles = result.outputs.converted_files
    # If one file was created, we get a string. If more than one, a list.
    # We want a list no matter what.
    if isinstance(outfiles, basestring):
        # The result is a string, not a list
        outfilesList = [outfiles]
    else:
        # The result is a list, not a string
        outfilesList = outfiles


    ##########
    # Upload results
    print
    print 'Preparing to upload files for scan %s.'%scanid

    # If we have a NIFTI resource and we've reached this point, we know overwrite=True.
    # We should delete the existing NIFTI resource.
    if hasNifti:
        print "Scan %s has a preexisting NIFTI resource. Deleting it now." % scanid
        try:
            r = requests.delete( url=host+"/data/experiments/%s/scans/%s/resources/NIFTI"%(session,scanid),
                headers=cookie, verify=False )
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            print "There was a problem deleting"
            print "    " + str( e )
            print "Skipping upload for scan %s." %scanid
            continue

    # Uploading
    for path in outfilesList:
        name = os.path.basename(path)

        print 'Uploading file %s for scan %s' % (name, scanid)
        r = requests.put(host+"/data/experiments/%s/scans/%s/resources/NIFTI/files/%s?format=NIFTI&content=NIFTI_RAW" % (session,scanid,name),
            headers=cookie, verify=False, files={'file':open(path, 'rb')})

    ##########
    # Clean up input directory
    print
    print 'Cleaning up %s directory.'%scanDicomDir
    for f in os.listdir(scanDicomDir):
        os.remove(os.path.join(scanDicomDir,f))

##########
# Clean up token
r = requests.delete( host+"/data/JSESSION", headers=cookie, verify=False )
print
print 'All done.'
