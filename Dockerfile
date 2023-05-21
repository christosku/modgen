FROM debian:bullseye-slim

# install dependencies for building
RUN apt-get update && apt-get install -y \
    acl bc curl cvs git mercurial \
    rsync subversion wget \
    bison bzip2 flex gawk gperf gzip help2man \
    nano perl patch tar texinfo unzip \
    automake binutils build-essential cpio \
    libtool libncurses-dev pkg-config \
    python-is-python3 libtool-bin \
    qemu-user-static

RUN useradd -m modgen
USER modgen
WORKDIR /home/modgen

RUN git clone https://github.com/moddevices/mod-plugin-builder/

WORKDIR /home/modgen/mod-plugin-builder

ARG INSTALL_MODDUOX=false
RUN if [ ${INSTALL_MODDUOX} = true ]; then \
    ./bootstrap.sh modduox-static minimal \
;fi

ARG INSTALL_MODDWARF=false
RUN if [ ${INSTALL_MODDWARF} = true ]; then \
    ./bootstrap.sh moddwarf minimal \
;fi


RUN git clone https://github.com/moddevices/max-gen-plugins/

WORKDIR /home/modgen/mod-plugin-builder/max-gen-plugins
RUN sed -i 's/git@github.com\:/https\:\/\/github.com\//' .gitmodules
RUN git submodule update --init --recursive

USER root
RUN apt-get install -y python3-pip

USER modgen
RUN mkdir -p /home/modgen/server
WORKDIR /home/modgen/server
# RUN mkdir -p /home/modgen/server/source
COPY requirements.txt /home/modgen/server
# COPY server.py /home/modgen/server
# COPY settings.ini /home/modgen/server
# COPY index.html /home/modgen/server
# COPY source/DistrhoPluginInfo.h /home/modgen/server/source
RUN pip3 install -r requirements.txt

# CMD ["python", "server.py"]