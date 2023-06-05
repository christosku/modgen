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
    ./bootstrap.sh modduox-new minimal \
;fi

ARG INSTALL_MODDWARF=false
RUN if [ ${INSTALL_MODDWARF} = true ]; then \
    ./bootstrap.sh moddwarf-new minimal \
;fi


RUN git clone https://github.com/moddevices/max-gen-plugins/

WORKDIR /home/modgen/mod-plugin-builder/max-gen-plugins
RUN sed -i 's/git@github.com\:/https\:\/\/github.com\//' .gitmodules
RUN git submodule update --init --recursive


WORKDIR /home/modgen/mod-plugin-builder
RUN git clone https://github.com/christosku/max-rnbo-plugins/

WORKDIR /home/modgen/mod-plugin-builder/max-rnbo-plugins
RUN git submodule update --init --recursive

USER root
RUN apt-get install -y python3-pip

USER modgen
RUN mkdir -p /home/modgen/server
WORKDIR /home/modgen/server
COPY requirements.txt /home/modgen/server
RUN pip3 install -r requirements.txt

COPY dpf.patch /home/modgen/server
RUN patch /home/modgen/mod-plugin-builder/max-rnbo-plugins/dpf/Makefile.base.mk dpf.patch
RUN patch /home/modgen/mod-plugin-builder/max-gen-plugins/dpf/Makefile.base.mk dpf.patch


# CMD ["python", "server.py"]