select * from read_parquet('{{ var("silver_root") }}/events.parquet')
