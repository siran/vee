FROM python:3.8

RUN apt update -y
# RUN apt install -y vim tar gzip curl wget xz

# WORKDIR /root
# RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
# RUN tar xvf ffmpeg-release-amd64-static.tar.xz
# RUN cp ffmpeg-6.0-amd64-static/ffmpeg-6.0-amd64-static /usr/bin

WORKDIR /var/task

COPY requirements.txt  .
# RUN  pip3 install -r requirements.txt

COPY src/* /var/task

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "flask", "run" ]

