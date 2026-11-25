select * from read_parquet('{{ var("silver_root") }}/frames.parquet')
