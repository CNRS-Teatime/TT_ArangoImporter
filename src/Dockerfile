FROM python:3.12-bookworm

LABEL authors="Marwan Ait Addi-Russier"
LABEL source.repo="https://github.com/CNRS-Teatime/TEATIME_PhD_Experiments"

ADD . .

RUN pip install -r requirements.txt

#Setting up environment variables as bash variables for entrypoint script
ENV THESO_CONFIG=${THESO_CONFIG}
ENV GRAPH_CONFIG=${GRAPH_CONFIG}
ENV DUMP_PATH=${DUMP_PATH}

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]