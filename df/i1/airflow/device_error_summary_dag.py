from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils import timezone
from datetime import timedelta

default_args = {
    'owner': 'iotadmin',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

with DAG(
    dag_id='device_error_summary',
    default_args=default_args,
    start_date=timezone.datetime(2025, 7, 30, 0),
    schedule='10 * * * *',  # 매시 10분마다
    catchup=False,
    max_active_runs=1,
    tags=['iot']
) as dag:

    spark_job = BashOperator(
        task_id='run_error_summary_job',
        bash_command="""ssh s1 'spark-submit /df/spark-summary/fms_summary.py {{ ((logical_date + macros.timedelta(hours=9)) - macros.timedelta(hours=1)).strftime('%Y%m%d%H') }}'""",
    )

    spark_job
