# Use Red Hat UBI 8.10 as the base image
FROM registry.access.redhat.com/ubi8/ubi:8.10

WORKDIR /hrbot
COPY . /hrbot

RUN yum update -y && \
    yum install -y \
            wget \
            nano \
            curl \
            python39 \
            python39-devel \
            python39-pip \
            gcc \
            gcc-c++ \
            libxml2-devel \
            zlib-devel \
            bzip2-devel \
            libffi-devel \
            iputils \
            net-tools && \
    yum clean all
RUN yum install -y git && \
    yum clean all && \
    rm -rf /var/cache/yum
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9

RUN python3.9 --version && which python3.9
RUN yum -y install epel-release || echo "EPEL already installed or not needed"

RUN dnf install -y xz && \
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ffmpeg.tar.xz && \
    tar -xf ffmpeg.tar.xz && \
    cp ffmpeg-*-static/ffmpeg /usr/local/bin/ && \
    cp ffmpeg-*-static/ffprobe /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg.tar.xz ffmpeg-*-static 
RUN python3.9 -m pip install --no-cache-dir  --default-timeout=5000 -r requirements.txt 
RUN python3.9 -m pip install --no-cache-dir  --upgrade pip torch --index-url https://download.pytorch.org/whl/cpu 
RUN python3.9 -m pip install --no-cache-dir  sentence-transformers protobuf==3.20.2
# Additional installations for IndicTrans2

# Clone IndicTransToolkit into the specified directory
RUN python3.9 -m pip install -U openai-whisper

COPY ai4bharat/models--sentence-transformers--all-MiniLM-L6-v2 /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2

RUN chmod -R 777 ./runner.sh && chmod +x /hrbot/runner.sh

EXPOSE 6001 6002 6003

CMD ["sh", "runner.sh"]