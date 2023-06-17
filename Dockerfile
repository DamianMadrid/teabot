# app/Dockerfile
FROM balenalib/aarch64-ubuntu:latest
# download requires apt dependencies
RUN apt-get update -y
RUN apt-get -y install curl gnupg python3.11 python3-pip software-properties-common
# add firefox repository and add priority and install
RUN  add-apt-repository ppa:mozillateam/ppa -y
RUN echo "Package: *\n\
Pin: release o=LP-PPA-mozillateam\n\
Pin-Priority: 1001" | tee /etc/apt/preferences.d/mozilla-firefox
RUN apt-get update -y
RUN apt-get install -y firefox
# sourcecode for sql and geckodriver binary 
RUN curl -LJO "https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux-aarch64.tar.gz"
RUN tar xzf geckodriver-v0.33.0-linux-aarch64.tar.gz  -C /usr/bin
RUN curl -O "https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz" && tar xzf sqlite-autoconf-3420000.tar.gz 
WORKDIR sqlite-autoconf-3420000
RUN ./configure && make && make install
WORKDIR ../
RUN rm -rf sqlite* && rm -rf geckodriver*
COPY . .
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3","main.py"]
