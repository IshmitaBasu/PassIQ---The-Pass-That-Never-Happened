select * from read_parquet('{{ var("silver_root") }}/passes.parquet')
