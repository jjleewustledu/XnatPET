#! /bin/bash
CONTAINER_NAME=$1
IMAGE_NAME=$2
CMD=$3

if [[ $# -eq 0 ]] ; then
    echo 'USAGE: docker rm some-container'
    echo 'USAGE: run_container.sh some-container [some-image] [some-command]'
    echo 'USAGE: # default some-image := `basename some-container -container`-image'
    exit 0
fi
if [[ $# -eq 1 ]] ; then
    IMAGE_NAME=`basename $1 -container`-image
    CMD=' '
fi
if [[ $# -eq 2 ]] ; then
    CMD=' '
fi

CONTAINER="docker run -it --rm --name $CONTAINER_NAME -v ${SINGULARITY_HOME}/:/SubjectsDir $IMAGE_NAME $CMD"
echo 'Starting container with commmand: '$CONTAINER
eval $CONTAINER
