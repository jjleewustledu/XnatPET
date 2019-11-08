# reference image: https://hub.docker.com/_/centos/
FROM centos
LABEL maintainer="John J. Lee <www.github.com/jjleewustledu>"
LABEL org.nrg.commands="[{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}, {\"required\": true, \"name\": \"SESSION_ID\", \"user-settable\": false}], \"name\": \"dcm2niix-scans-batch\", \"command-line\": \"batch-launch.py scans \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-scan #SESSION_ID# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-scan on all scans in a session\", \"contexts\": [\"xnat:imageSessionData\"], \"name\": \"dcm2niix-scans-batch-session\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Session\", \"name\": \"session\", \"description\": \"Input session\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project\", \"derived-from-xnat-object-property\": \"project-id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"session\", \"type\": \"string\"}, {\"provides-value-for-command-input\": \"SESSION_ID\", \"name\": \"session-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"session\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of scans\"}, \
	{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}, {\"required\": true, \"name\": \"SUBJECT_ID\", \"user-settable\": false}], \"name\": \"dcm2niix-experiments_list-batch\", \"command-line\": \"batch-launch.py experiments_list \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-scans-batch-session #SUBJECT_ID# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-scans-batch-session on all experiments_list in a subject\", \"contexts\": [\"xnat:subjectData\"], \"name\": \"dcm2niix-experiments_list-batch-subject\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Subject\", \"name\": \"subject\", \"description\": \"Input subject\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project\", \"derived-from-xnat-object-property\": \"project-id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"subject\", \"type\": \"string\"}, {\"provides-value-for-command-input\": \"SUBJECT_ID\", \"name\": \"subject-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"subject\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of experiments_list\"}, \
	{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}], \"name\": \"dcm2niix-subjects-batch\", \"command-line\": \"batch-launch.py subjects \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-experiments_list-batch-subject #PROJECT# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-experiments_list-batch-subject on all subjects in a project\", \"contexts\": [\"xnat:projectData\"], \"name\": \"dcm2niix-subjects-batch-project\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Project\", \"name\": \"project\", \"description\": \"Input project\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"project\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of subjects\"}]"

# setup centos
RUN yum update -y && \
    yum install -y wget bzip2 ca-certificates \
    build-essential \
    curl \
    emacs-nox \
    git-core \
    htop \
    pkg-config \
    python2-dev \
    python2-pip \
    python-httplib2 \
    python-matplotlib \
    python-networkx \
    python-nose \
    python-setuptools \
    python-virtualenv \
    python-lxml \
    unzip && \
    yum clean all

# setup anaconda; consider using miniconda
RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && \
    wget --quiet https://repo.continuum.io/archive/Anaconda2-2018.12-Linux-x86_64.sh -O ~/anaconda.sh && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh

ENV PATH /opt/conda/bin:$PATH

RUN conda update conda && \
    conda install -y                coverage==3.7.1 docopt glob2 lxml==3.2.1 matplotlib networkx nose==1.2.1 requests && \
    conda install -y -c conda-forge pydicom httplib2 urllib3
    # requests=2.1.0 was working

RUN pip --no-cache-dir install --upgrade \
    jsonpath \
    pixiedust 

# setup filesystem
RUN mkdir /work && mkdir /SubjectsDir
ENV SHELL=/bin/bash
VOLUME /work
VOLUME /SubjectsDir

# setup pyxnat, interfile packages
# https://stackoverflow.com/questions/26392227/python-setup-py-install-does-not-work-from-dockerfile-but-i-can-go-in-the-cont
ADD pyxnat /work/pyxnat
ADD interfile /work/interfile
ADD xnatpet /work/xnatpet
ADD setup.py /work/setup.py
ADD README.md /work/README.md
RUN cd /work/pyxnat/    && python setup.py install && \
    cd /work/interfile/ && python setup.py install && \
    cd /work/           && python setup.py install # xnatpet
# Aternatively, install pyxnat, interfile and xnatpet manually using finish_Docker_installs.sh,
# then issue:
# > docker commit xnatpet-container jjleewustledu/xnatpet-image:test
# > docker push jjleewustledu/xnatpet-image:test
# cluster> singularity pull docker://jjleewustledu/xnatpet-image:test

# run xnatpet.py; replace "-h" with:
# "-c", "<cachedir>"
# "-p", "<project>", 
# "-s", "<constaints>"
WORKDIR    /SubjectsDir
ENTRYPOINT ["python", "/work/xnatpet/xnatpet.py"]
CMD        ["-h"]

