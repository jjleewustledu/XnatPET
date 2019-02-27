# XnatPET


    $ python xnatpet.py -h
    usage: xnatpet.py [-h] -p <path> -j <ID> -c
    ['<param>', '<logical>', '<value>', '<LOGICAL>']
    
##xnatpet stages data from XNAT server to local filesystem;

    e.g.:  python xnatpet.py -p /path/to/projects -j PROJECT_ID \
                             -c [('xnat:petSessionData/DATE', '>', '2018-01-01'), 'AND']
    
    optional arguments:
    -h, --help            show this help message and exit
    -p <path>, --prefix <path>
    path containing project-level data
    -j <ID>, --proj <ID>  project ID as known by XNAT
    -c [('<param>', '<logical>', '<value>'), '<LOGICAL>'], --constraints [('<param>', '<logical>', '<value>'), '<LOGICAL>']
    must express the constraint API of pyxnat;see also htt
    ps://groups.google.com/forum/#!topic/xnat_discussion/S
    HWAxHNb570