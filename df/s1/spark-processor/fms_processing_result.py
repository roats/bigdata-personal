from pyspark.sql import SparkSession
from pyspark.sql.types import StructType

# SparkSession 초기화
spark = SparkSession.builder \
    .appName("Read All Parquet Files in Processed Directories (v2)") \
    .getOrCreate()

# processed 디렉터리는 파티션 폴더 없이 바로 Parquet 파일이 저장됨
main_path = "hdfs://s1:9000/fms/processed/main/"
alert_path = "hdfs://s1:9000/fms/processed/alert/"
quarantine_path = "hdfs://s1:9000/fms/processed/quarantine/"

empty_schema = StructType([])

def safe_read_parquet(path, label):
    print(f"\n[INFO] 시도하는 경로: {path}")
    try:
        df = spark.read.parquet(path)
        print(f"[SUCCESS] {label} 데이터 로드 완료")
        return df
    except Exception as e:
        print(f"[FAIL] {label} 데이터 로드 실패: {e}")
        return spark.createDataFrame([], empty_schema)

df_main = safe_read_parquet(main_path, "main")
df_main.show()

df_alert = safe_read_parquet(alert_path, "alert")
df_alert.show()

df_quarantine = safe_read_parquet(quarantine_path, "quarantine")
df_quarantine.show()