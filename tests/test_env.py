import duckdb


def test_duckdb_runs():
    assert duckdb.sql("select 1 as x").fetchall() == [(1,)]
