FROM apache/airflow:3.3.1-python3.11

ARG AIRFLOW_VERSION=3.3.1

COPY --chown=airflow:0 airflow/requirements.txt /tmp/clinsight-airflow-requirements.txt
RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/clinsight-airflow-requirements.txt \
    && pip check

COPY --chown=airflow:0 backend /opt/clinsight/backend
COPY --chown=airflow:0 dbt /opt/clinsight/dbt
COPY --chown=airflow:0 airflow/dags /opt/airflow/dags
