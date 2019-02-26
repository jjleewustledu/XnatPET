# reference image: https://hub.docker.com/_/centos/
FROM centos
LABEL maintainer="John J. Lee <www.github.com/jjleewustledu>"
LABEL org.nrg.commands="[{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}, {\"required\": true, \"name\": \"SESSION_ID\", \"user-settable\": false}], \"name\": \"dcm2niix-scans-batch\", \"command-line\": \"batch-launch.py scans \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-scan #SESSION_ID# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-scan on all scans in a session\", \"contexts\": [\"xnat:imageSessionData\"], \"name\": \"dcm2niix-scans-batch-session\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Session\", \"name\": \"session\", \"description\": \"Input session\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project\", \"derived-from-xnat-object-property\": \"project-id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"session\", \"type\": \"string\"}, {\"provides-value-for-command-input\": \"SESSION_ID\", \"name\": \"session-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"session\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of scans\"}, \
	{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}, {\"required\": true, \"name\": \"SUBJECT_ID\", \"user-settable\": false}], \"name\": \"dcm2niix-sessions-batch\", \"command-line\": \"batch-launch.py sessions \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-scans-batch-session #SUBJECT_ID# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-scans-batch-session on all sessions in a subject\", \"contexts\": [\"xnat:subjectData\"], \"name\": \"dcm2niix-sessions-batch-subject\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Subject\", \"name\": \"subject\", \"description\": \"Input subject\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project\", \"derived-from-xnat-object-property\": \"project-id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"subject\", \"type\": \"string\"}, {\"provides-value-for-command-input\": \"SUBJECT_ID\", \"name\": \"subject-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"subject\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of sessions\"}, \
	{\"inputs\": [{\"required\": true, \"name\": \"PROJECT\", \"user-settable\": false}], \"name\": \"dcm2niix-subjects-batch\", \"command-line\": \"batch-launch.py subjects \$XNAT_HOST \$XNAT_USER \$XNAT_PASS dcm2niix-sessions-batch-subject #PROJECT# #PROJECT#\", \"outputs\": [], \"image\": \"xnat/batch-launch:1.0\", \"override-entrypoint\": true, \"version\": \"1.0\", \"schema-version\": \"1.0\", \"xnat\": [{\"description\": \"Launch dcm2niix-sessions-batch-subject on all subjects in a project\", \"contexts\": [\"xnat:projectData\"], \"name\": \"dcm2niix-subjects-batch-project\", \"output-handlers\": [], \"label\": \"dcm2niix batch\", \"external-inputs\": [{\"load-children\": false, \"required\": true, \"type\": \"Project\", \"name\": \"project\", \"description\": \"Input project\"}], \"derived-inputs\": [{\"provides-value-for-command-input\": \"PROJECT\", \"name\": \"project-id\", \"derived-from-xnat-object-property\": \"id\", \"required\": true, \"user-settable\": false, \"derived-from-wrapper-input\": \"project\", \"type\": \"string\"}]}], \"mounts\": [], \"type\": \"docker\", \"description\": \"Launch dcm2niix containers on a batch of subjects\"}]"

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
    python-setuptools \
    python-virtualenv \
    unzip && \
    yum clean all

# setup anaconda; consider using miniconda
RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && \
    wget --quiet https://repo.continuum.io/archive/Anaconda2-2018.12-Linux-x86_64.sh -O ~/anaconda.sh && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh

ENV PATH /opt/conda/bin:$PATH

RUN pip --no-cache-dir install --upgrade \
    docopt \
    httplib2 \
    jsonpath \
    lxml \
    nose \
    pixiedust \
    requests && \
    conda install -y -c conda-forge pydicom

# setup filesystem
RUN mkdir work
ENV HOME=/work
ENV SHELL=/bin/bash
VOLUME /work

# setup pyxnat, interfile packages
WORKDIR /work
RUN git clone https://github.com/jjleewustledu/pyxnat.git && git clone https://github.com/jjleewustledu/interfile.git
#WORKDIR /work/pyxnat
#RUN python setup.py install
#WORKDIR /work/interfile
#RUN python setup.py install
#WORKDIR /work
#RUN python setup.py install # xnatpet
# Aternatively, install pyxnat, interfile and xnatpet manually, then issue
# > docker commit xnatpet-container jjleewustedu/xnatpet-image:manual_install

# setup NRG XNAT Docker
ENV CNDA_UID $CNDA_UID
ENV CNDA_PWD $CNDA_PWD
WORKDIR /work
COPY orchestrate.py /usr/local/bin

# setup jupyter
WORKDIR /work
EXPOSE 7745
ADD run_jupyter.sh /work/run_jupyter.sh
RUN chmod +x /work/run_jupyter.sh

CMD ["./run_jupyter.sh"]
