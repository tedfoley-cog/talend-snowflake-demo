# Component Translation Rules — Talend to Python/Snowflake

## Database Components

### tDBInput → Snowpark `session.table()` / `session.sql()`

| Talend | Python/Snowpark |
|---|---|
| `tDBInput` with `QUERY` parameter | `session.sql("SELECT ...")` |
| `tDBInput` with `TABLE` parameter | `session.table("schema.table_name")` |
| Context variable `context.src_db_host` | Snowflake connection config (no host needed) |
| `DB_VERSION = "ORACLE_12"` | Source extraction via `snowflake-connector-python` or pre-staged data |

```python
# Talend: tDBInput reading from CUSTOMER_MASTER with SQL query
# Python equivalent:
df = session.sql("""
    SELECT CUSTOMER_ID, FIRST_NAME, LAST_NAME, SSN, EMAIL
    FROM CUSTOMER_MASTER
    WHERE LAST_UPDATED >= :batch_date
""")
```

### tDBOutput → Snowpark `DataFrame.write`

| Talend Action | Snowpark Equivalent |
|---|---|
| `DATA_ACTION = "INSERT"` | `df.write.mode("append").save_as_table("TABLE")` |
| `DATA_ACTION = "UPDATE"` | `session.sql("MERGE INTO ... WHEN MATCHED THEN UPDATE ...")` |
| `DATA_ACTION = "INSERT_OR_UPDATE"` | `session.sql("MERGE INTO ... WHEN MATCHED THEN UPDATE WHEN NOT MATCHED THEN INSERT ...")` |
| `DATA_ACTION = "DELETE"` | `session.sql("DELETE FROM table WHERE ...")` |

```python
# Talend: tDBOutput INSERT to STG_CUSTOMER
# Python equivalent:
df_output.write.mode("append").save_as_table("RAW.STG_CUSTOMER")
```

### tDBRow → `session.sql()`

| Talend | Python/Snowpark |
|---|---|
| Dynamic SQL via string concatenation | Parameterized `session.sql()` |
| Row-by-row UPDATE | Batch MERGE statement |

```python
# Talend: tDBRow executing UPDATE per row
# Python equivalent (batch):
session.sql("""
    MERGE INTO LOAN_APPLICATION tgt
    USING LOAN_RISK_SCORES src ON tgt.APPLICATION_ID = src.APPLICATION_ID
    WHEN MATCHED THEN UPDATE SET
        tgt.STATUS = src.DECISION,
        tgt.RISK_SCORE = src.RISK_SCORE,
        tgt.LAST_UPDATED = CURRENT_TIMESTAMP()
""")
```

## Transformation Components

### tMap → pandas / Snowpark transformations

| Talend tMap Feature | Python Equivalent |
|---|---|
| Column mapping (`row1.COL`) | `df["COL"]` or `df.col("COL")` |
| Expression (`row1.A + " " + row1.B`) | `F.concat(df["A"], F.lit(" "), df["B"])` |
| Filter (`expressionFilter`) | `df.filter(condition)` |
| Var table | Intermediate variables / `df.with_column()` |
| Lookup join (`row2`) | `df1.join(df2, on="KEY")` |
| Reject output | `df.filter(~condition)` |
| Ternary (`cond ? a : b`) | `F.when(cond, a).otherwise(b)` |
| Null check (`x != null`) | `F.col("x").is_not_null()` |

```python
# Talend: tMap with FULL_NAME = row1.FIRST_NAME + " " + row1.LAST_NAME
# Python equivalent:
from snowflake.snowpark import functions as F

df = df.with_column("FULL_NAME",
    F.concat(F.col("FIRST_NAME"), F.lit(" "), F.col("LAST_NAME"))
)
```

```python
# Talend: tMap with lookup join on LOAN_ID
# Python equivalent:
df_result = df_payments.join(
    df_balances,
    on="LOAN_ID",
    how="left"
).with_column("VARIANCE",
    F.abs(F.col("PAYMENT_AMOUNT") - F.col("MONTHLY_PAYMENT_DUE"))
)
```

## File Components

### tFileInputDelimited → `csv.reader` / `pd.read_csv`

| Talend | Python |
|---|---|
| `FILENAME` parameter | `pd.read_csv(filepath)` |
| `HEADER = "1"` | `header=0` (default) |
| `FIELDSEPARATOR = ","` | `sep=","` |
| `CSV_OPTION = true` | `quoting=csv.QUOTE_ALL` |
| `ENCODING = "UTF-8"` | `encoding="utf-8"` |

```python
# Talend: tFileInputDelimited reading daily_loan_applications.csv
# Python equivalent:
import pandas as pd

df = pd.read_csv(
    "/data/incoming/loan_apps/daily_loan_applications.csv",
    encoding="utf-8",
    dtype={"APPLICATION_ID": str, "CUSTOMER_ID": str}
)
```

### tFileOutputDelimited → `csv.writer` / `pd.to_csv`

| Talend | Python |
|---|---|
| `FILENAME` parameter | `df.to_csv(filepath)` |
| `FIELDSEPARATOR = "\|"` | `sep="\|"` |
| `INCLUDEHEADER = true` | `header=True` |
| `APPEND = false` | `mode="w"` |

```python
# Talend: tFileOutputDelimited writing discrepancy report
# Python equivalent:
df.to_csv(
    f"/data/reports/discrepancies/discrepancy_report_{report_date}.csv",
    index=False,
    encoding="utf-8"
)
```

## Logging / Debug

### tLogRow → `logging` module

| Talend | Python |
|---|---|
| `TABLE_PRINT = true` | `logger.info(df.to_string())` |
| `PRINT_HEADER = true` | Include column names |
| `PRINT_CONTENT_WITH_LOG4J = true` | `logging.getLogger()` |

```python
import logging
logger = logging.getLogger("etl")
logger.info("Invalid records:\n%s", df_invalid.to_string())
```

## Job Lifecycle

### tPrejob / tPostjob → Python context managers

```python
# Talend: tPrejob (setup) → main flow → tPostjob (cleanup)
# Python equivalent:
from contextlib import contextmanager

@contextmanager
def etl_job_context(job_name: str, session):
    logger.info(f"Starting job: {job_name}")
    session.sql(f"INSERT INTO ETL_LOG VALUES ('{job_name}', CURRENT_TIMESTAMP(), 'RUNNING')")
    try:
        yield session
        session.sql(f"UPDATE ETL_LOG SET STATUS='SUCCESS', END_TS=CURRENT_TIMESTAMP() WHERE JOB_NAME='{job_name}'")
    except Exception as e:
        session.sql(f"UPDATE ETL_LOG SET STATUS='FAILED', END_TS=CURRENT_TIMESTAMP() WHERE JOB_NAME='{job_name}'")
        raise
```

## Custom Java Routines → Python Functions

### DateFormatUtils.java → `date_utils.py`

| Java | Python |
|---|---|
| `SimpleDateFormat.parse()` | `datetime.strptime()` |
| `SimpleDateFormat.format()` | `datetime.strftime()` |
| `getFiscalQuarter(date)` | Custom function with same logic |

### AmountUtils.java → `amount_utils.py`

| Java | Python |
|---|---|
| `BigDecimal.setScale(n, HALF_UP)` | `round(value, n)` or `Decimal` |
| `NumberFormat.getCurrencyInstance()` | `locale.currency()` or f-string |
| `calculateMonthlyPayment()` | Same amortization formula |

### AccountValidator.java → `validators.py`

| Java | Python |
|---|---|
| `Pattern.compile()` / `.matches()` | `re.compile()` / `.match()` |
| Luhn algorithm | Same algorithm in Python |
| `isValidSSN()` | Same validation rules |

## Context Variables → Configuration

| Talend | Python |
|---|---|
| `context.src_db_host` | `config["src_db_host"]` or env var |
| `context.batch_date` | CLI argument or config |
| `context.tgt_schema` | Snowflake session config |
| `contextParameter type="id_Password"` | Secret manager / env var |
