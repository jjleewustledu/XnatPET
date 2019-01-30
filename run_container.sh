#! /bin/bash

docker run -it --name xnatpet-container --rm --net=host -v ${HOME2}/Docker/XnatPET/:/ds xnatpet-image
