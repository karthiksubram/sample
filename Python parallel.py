import pyodbc
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import os
import io # To simulate blob data if needed for testing

# --- Configuration ---
DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',  # e.g., '{ODBC Driver 17 for SQL Server}', '{PostgreSQL Unicode(x64)}'
    'server': 'your_db_server',
    'database': 'your_database',
    'uid': 'your_username',
    'pwd': 'your_password'
}

# Table and column names (adjust as per your schema)
TABLE1_NAME = 'YourSourceTable1'
TABLE1_BUSINESS_DATE_COL = 'businessdate'
TABLE1_ID_COL = 'id'

TABLE2_NAME = 'YourSourceTable2'
TABLE2_BUSINESS_DATE_COL = 'businessdate'
TABLE2_ID_COL = 'id'
# Dynamically generate 30 blob column names for the query
BLOB_COLUMNS = [f'blob_col_{i}' for i in range(1, 31)]
TABLE2_DATA_COLS_STR = ', '.join(BLOB_COLUMNS)

TARGET_TABLE_NAME = 'YourTargetTable'
# Example columns for the target table (adjust based on what you derive from matrix ops)
# You might insert the result matrix, or summary statistics
TARGET_TABLE_COL1 = 'result_matrix_sum'       # Example: Sum of the resulting matrix
TARGET_TABLE_COL2 = 'result_matrix_max_val' # Example: Max value of the resulting matrix
TARGET_TABLE_COL3 = 'businessdate_col'
TARGET_TABLE_COL4 = 'id_col'

# Query 1: Get keys (businessdate, id)
QUERY1_TEMPLATE = f"""
SELECT {TABLE1_BUSINESS_DATE_COL}, {TABLE1_ID_COL}
FROM {TABLE1_NAME}
WHERE {TABLE1_BUSINESS_DATE_COL} >= ? AND {TABLE1_BUSINESS_DATE_COL} < ?
ORDER BY {TABLE1_BUSINESS_DATE_COL}, {TABLE1_ID_COL};
"""

# Query 2: Get data from Table 2 for a specific businessdate and ID
# IMPORTANT: Since you need 30 BLOBs per ID, this query now needs to be called per ID,
# or if possible, fetch multiple IDs at once IF your DB driver supports it and it's efficient.
# For simplicity, we will still query per ID within the batch loop for clarity.
QUERY2_TEMPLATE = f"""
SELECT {TABLE2_DATA_COLS_STR}
FROM {TABLE2_NAME}
WHERE {TABLE2_BUSINESS_DATE_COL} = ? AND {TABLE2_ID_COL} = ?;
"""

# Insert query into Target Table for executemany
INSERT_QUERY_TEMPLATE = f"""
INSERT INTO {TARGET_TABLE_NAME} ({TARGET_TABLE_COL1}, {TARGET_TABLE_COL2}, {TARGET_TABLE_COL3}, {TARGET_TABLE_COL4})
VALUES (?, ?, ?, ?);
"""

# Parallelization settings
RECOMMENDED_MAX_WORKERS = os.cpu_count()
MAX_WORKERS = min(RECOMMENDED_MAX_WORKERS if RECOMMENDED_MAX_WORKERS else 1, 12) # Capped example

# Batching settings
BATCH_SIZE = 1000 # Number of records to process and insert in one batch

# Time range for data extraction (1.5 years from today)
END_DATE = datetime.now().date()
START_DATE = END_DATE - timedelta(days=int(1.5 * 365))

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes and returns a database connection."""
    conn_str = (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['uid']};"
        f"PWD={DB_CONFIG['pwd']};"
    )
    try:
        conn = pyodbc.connect(conn_str)
        conn.autocommit = False
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Database connection error: {sqlstate}")
        raise

# --- Step 1: Get Keys (businessdate + id) and Group by BusinessDate ---
def get_and_group_keys_from_table1():
    """
    Executes Query 1 to get unique (businessdate, id) pairs and groups them by businessdate.
    Returns a dictionary: {businessdate: [id1, id2, ...], ...}.
    """
    print(f"--- Step 1: Retrieving keys from {TABLE1_NAME} and grouping ---")
    start_time = time.perf_counter()
    grouped_keys = defaultdict(list)
    total_ids = 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(QUERY1_TEMPLATE, START_DATE, END_DATE)
            for row in cursor:
                b_date = row[TABLE1_BUSINESS_DATE_COL]
                rec_id = row[TABLE1_ID_COL]
                grouped_keys[b_date].append(rec_id)
                total_ids += 1
        end_time = time.perf_counter()
        print(f"Step 1 completed. Found {total_ids} IDs across {len(grouped_keys)} business dates in {end_time - start_time:.4f} seconds.")
        return grouped_keys, (end_time - start_time)
    except Exception as e:
        print(f"Error in Step 1: {e}")
        return defaultdict(list), 0

# --- Helper to convert BLOB to NumPy Array ---
def parse_blob_to_numpy_array(blob_data):
    """
    This is a placeholder function. You NEED to customize this based on
    how your 5000-element arrays are stored in the BLOB columns.

    Common scenarios:
    1. Text (e.g., comma-separated string):
       return np.array([float(x) for x in blob_data.decode('utf-8').split(',')])
    2. Binary (e.g., raw bytes of a numpy array):
       return np.frombuffer(blob_data, dtype=np.float32) # Or np.float64
    3. Pickled Python object:
       import pickle; return pickle.loads(blob_data)

    For demonstration, we'll assume it's a simple byte string representing numbers.
    """
    if isinstance(blob_data, memoryview): # pyodbc might return memoryview for binary
        blob_data = blob_data.tobytes()
    elif isinstance(blob_data, str): # If your DB driver returns string
        pass # Already string
    elif not isinstance(blob_data, bytes): # If something else, try converting
        blob_data = str(blob_data).encode('utf-8')

    try:
        # Example 1: Comma-separated string of numbers in bytes
        # Assume each element is float
        return np.array([float(x) for x in blob_data.decode('utf-8').split(',')], dtype=np.float32)
    except (UnicodeDecodeError, ValueError) as e:
        print(f"Warning: Could not parse BLOB data into numpy array. Error: {e}")
        # Return a zero array or handle appropriately
        return np.zeros(5000, dtype=np.float32)

# --- Step 2 & 3: Process and Insert for a single business_date and its IDs ---
def process_business_date_data(business_date, ids_for_date, batch_size):
    """
    For a given business_date, iterates through its IDs,
    fetches BLOBs, performs matrix operations, and batches inserts.
    """
    conn = None
    b_date_start_time = time.perf_counter()
    daily_query2_total_time = 0
    daily_matrix_ops_total_time = 0
    daily_insert_total_time = 0
    daily_records_processed = 0
    daily_errors = 0
    results_detail = [] # To store individual (query2, matrix_ops, insert) times for analysis

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Split IDs into batches
        id_batches = [ids_for_date[i:i + batch_size] for i in range(0, len(ids_for_date), batch_size)]

        for batch_num, batch_ids in enumerate(id_batches):
            batch_insert_data = [] # Data for executemany for this batch
            batch_processing_start_time = time.perf_counter()
            
            for record_id in batch_ids:
                try:
                    # Measure Query 2 time per ID
                    query2_start_time = time.perf_counter()
                    cursor.execute(QUERY2_TEMPLATE, business_date, record_id)
                    table2_results = cursor.fetchall()
                    query2_end_time = time.perf_counter()
                    query2_duration = query2_end_time - query2_start_time
                    daily_query2_total_time += query2_duration

                    if not table2_results:
                        results_detail.append({'bd': business_date, 'id': record_id, 'q2_time': query2_duration, 'matrix_time': 0, 'ins_time': 0, 'status': 'No data'})
                        continue

                    data_row = table2_results[0] # Assuming one row per (businessdate, id)
                    
                    matrix_ops_start_time = time.perf_counter()
                    
                    # --- Complex Matrix Processing for this ID ---
                    matrices = []
                    for i in range(30): # Loop through 30 BLOB columns
                        blob_data = data_row[i]
                        # CALL YOUR CUSTOMIZED BLOB PARSING FUNCTION HERE
                        arr = parse_blob_to_numpy_array(blob_data)
                        if arr.shape[0] != 5000:
                            raise ValueError(f"BLOB array for {business_date}-{record_id} column {i+1} does not have 5000 elements (got {arr.shape[0]})")
                        matrices.append(arr)

                    # Example matrix operation: Sum the first 15, subtract the next 15
                    # Initialize with the first matrix to handle dimensions correctly
                    if not matrices:
                        # Should not happen if data_row has 30 columns
                        processed_value1 = 0
                        processed_value2 = 0
                    else:
                        result_matrix = np.copy(matrices[0]) # Start with the first matrix
                        for i in range(1, 15):
                            result_matrix += matrices[i]
                        for i in range(15, 30):
                            result_matrix -= matrices[i]

                        # Derive some processed values for insertion
                        processed_value1 = np.sum(result_matrix) # Example: Sum of the resulting matrix
                        processed_value2 = np.max(result_matrix) # Example: Max value of the resulting matrix
                    
                    matrix_ops_end_time = time.perf_counter()
                    matrix_ops_duration = matrix_ops_end_time - matrix_ops_start_time
                    daily_matrix_ops_total_time += matrix_ops_duration

                    # Add processed data for this ID to the batch list
                    batch_insert_data.append((processed_value1, processed_value2, business_date, record_id))
                    results_detail.append({'bd': business_date, 'id': record_id, 'q2_time': query2_duration, 'matrix_time': matrix_ops_duration, 'ins_time': 0, 'status': 'Prepared for batch'})

                except Exception as e_id:
                    print(f"Error processing {business_date}, ID {record_id}: {e_id}")
                    daily_errors += 1
                    results_detail.append({'bd': business_date, 'id': record_id, 'q2_time': 0, 'matrix_time': 0, 'ins_time': 0, 'status': f'Error: {e_id}'})
                    # Do not add to batch_insert_data if there was an error with this ID

            # --- Execute batch insert ---
            if batch_insert_data:
                insert_start_time = time.perf_counter()
                try:
                    cursor.executemany(INSERT_QUERY_TEMPLATE, batch_insert_data)
                    conn.commit() # Commit the batch
                    inserted_count = len(batch_insert_data)
                    daily_records_processed += inserted_count
                    insert_end_time = time.perf_counter()
                    insert_duration = insert_end_time - insert_start_time
                    daily_insert_total_time += insert_duration
                    print(f"  Batch {batch_num+1}/{len(id_batches)} for {business_date}: Inserted {inserted_count} records in {insert_duration:.4f}s.")
                    # Update status for records in this batch
                    for item in results_detail:
                        if item['status'] == 'Prepared for batch' and (item['bd'], item['id']) in [(d[2], d[3]) for d in batch_insert_data]:
                            item['ins_time'] = insert_duration / inserted_count if inserted_count > 0 else 0 # Avg time per record in batch
                            item['status'] = 'Success'

                except pyodbc.Error as batch_insert_ex:
                    conn.rollback() # Rollback the entire batch on error
                    print(f"Batch insert error for {business_date} (Batch {batch_num+1}): {batch_insert_ex}")
                    daily_errors += len(batch_ids) # Assume all in batch failed for error count
                    # Mark all relevant results_detail items as failed
                    for item in results_detail:
                        if item['status'] == 'Prepared for batch' and (item['bd'], item['id']) in [(d[2], d[3]) for d in batch_insert_data]:
                            item['status'] = f'Batch Insert Error: {batch_insert_ex}'
                except Exception as e_batch:
                    conn.rollback()
                    print(f"Unexpected error during batch insert for {business_date} (Batch {batch_num+1}): {e_batch}")
                    daily_errors += len(batch_ids)
                    for item in results_detail:
                        if item['status'] == 'Prepared for batch' and (item['bd'], item['id']) in [(d[2], d[3]) for d in batch_insert_data]:
                            item['status'] = f'Unexpected Batch Error: {e_batch}'
            else:
                print(f"  Batch {batch_num+1}/{len(id_batches)} for {business_date}: No data to insert.")


        b_date_end_time = time.perf_counter()
        print(f"Finished processing business_date {business_date}. Total time: {b_date_end_time - b_date_start_time:.4f}s")
        # Final commit for the entire business_date is redundant if auto-committing per batch

        return {
            'business_date': business_date,
            'total_ids_for_date': len(ids_for_date),
            'processed_records': daily_records_processed,
            'total_query2_time': daily_query2_total_time,
            'total_matrix_ops_time': daily_matrix_ops_total_time,
            'total_insert_time': daily_insert_total_time,
            'daily_processing_time': b_date_end_time - b_date_start_time,
            'errors': daily_errors,
            'detail_results': results_detail
        }
    except Exception as e_date:
        if conn: conn.rollback()
        print(f"Major error processing business_date {business_date} (Process-level): {e_date}")
        return {
            'business_date': business_date,
            'total_ids_for_date': len(ids_for_date),
            'processed_records': 0,
            'total_query2_time': 0,
            'total_matrix_ops_time': 0,
            'total_insert_time': 0,
            'daily_processing_time': 0,
            'errors': len(ids_for_date),
            'status': f'Major Error: {e_date}',
            'detail_results': []
        }
    finally:
        if conn:
            conn.close()

# --- Main Program ---
def main():
    overall_start_time = time.perf_counter()

    # Step 1: Get keys and group them by businessdate
    grouped_keys_by_date, step1_time = get_and_group_keys_from_table1()
    if not grouped_keys_by_date:
        print("No business dates to process. Exiting.")
        return

    print(f"\n--- Step 2 & 3: Processing and Inserting data for {len(grouped_keys_by_date)} business dates (Parallel) ---")

    all_query2_times = []
    all_matrix_ops_times = []
    all_insert_times = []
    total_q2_time_overall = 0
    total_matrix_ops_time_overall = 0
    total_insert_time_overall = 0
    total_processed_ids_overall = 0
    total_errors_overall = 0
    daily_processing_durations = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_date = {
            executor.submit(process_business_date_data, b_date, ids, BATCH_SIZE): b_date
            for b_date, ids in grouped_keys_by_date.items()
        }

        for future in as_completed(future_to_date):
            b_date = future_to_date[future]
            try:
                result = future.result()
                daily_processing_durations.append(result['daily_processing_time'])
                total_q2_time_overall += result['total_query2_time']
                total_matrix_ops_time_overall += result['total_matrix_ops_time']
                total_insert_time_overall += result['total_insert_time']
                total_processed_ids_overall += result['processed_records']
                total_errors_overall += result['errors']

                # We can't directly add individual insert times from `detail_results`
                # if they are averaged per batch, so we'll just track aggregated.
                # However, for Q2 and matrix ops, they are per-ID sums within the process.
                for item in result['detail_results']:
                    all_query2_times.append(item['q2_time'])
                    all_matrix_ops_times.append(item['matrix_time'])
                    # Only add if it was successfully inserted (status == 'Success')
                    if item['status'] == 'Success':
                        all_insert_times.append(item['ins_time'])


                if 'status' in result and 'Error' in result['status']:
                    print(f"Business Date {b_date} processing had a major error: {result['status']}")

            except Exception as exc:
                print(f'Business Date {b_date} generated an unhandled exception: {exc}')
                total_errors_overall += len(grouped_keys_by_date[b_date]) # Assume all IDs for this date failed

    overall_end_time = time.perf_counter()
    overall_duration = overall_end_time - overall_start_time

    print("\n--- Summary Report ---")
    print(f"Overall execution time (including Step 1): {overall_duration:.4f} seconds")
    print(f"Step 1 (Key Retrieval & Grouping) time: {step1_time:.4f} seconds")
    print(f"Total business dates processed: {len(grouped_keys_by_date)}")
    print(f"Total individual IDs identified in Step 1: {sum(len(ids) for ids in grouped_keys_by_date.values())}")
    print(f"Total records successfully processed and inserted: {total_processed_ids_overall}")
    print(f"Total errors encountered (ID-level): {total_errors_overall}")

    if daily_processing_durations:
        print(f"\n--- Daily Processing Times ---")
        print(f"Average daily processing time: {sum(daily_processing_durations) / len(daily_processing_durations):.4f} seconds/day")
        print(f"Max daily processing time: {max(daily_processing_durations):.4f} seconds/day")
        print(f"Min daily processing time: {min(daily_processing_durations):.4f} seconds/day")

    if all_query2_times:
        print(f"\n--- Individual Query 2 Times (per ID) ---")
        print(f"Average Query 2 time per ID: {sum(all_query2_times) / len(all_query2_times):.6f} seconds")
        print(f"Max Query 2 time per ID: {max(all_query2_times):.6f} seconds")
        print(f"Min Query 2 time per ID: {min(all_query2_times):.6f} seconds")
        print(f"Total cumulative Query 2 time across all IDs: {total_q2_time_overall:.4f} seconds")

    if all_matrix_ops_times:
        print(f"\n--- Individual Matrix Operation Times (per ID) ---")
        print(f"Average Matrix Op time per ID: {sum(all_matrix_ops_times) / len(all_matrix_ops_times):.6f} seconds")
        print(f"Max Matrix Op time per ID: {max(all_matrix_ops_times):.6f} seconds")
        print(f"Min Matrix Op time per ID: {min(all_matrix_ops_times):.6f} seconds")
        print(f"Total cumulative Matrix Op time across all IDs: {total_matrix_ops_time_overall:.4f} seconds")

    if all_insert_times:
        print(f"\n--- Individual Insert Times (per Successfully Inserted Record) ---")
        print(f"Average Insert time per record: {sum(all_insert_times) / len(all_insert_times):.6f} seconds")
        print(f"Max Insert time per record: {max(all_insert_times):.6f} seconds")
        print(f"Min Insert time per record: {min(all_insert_times):.6f} seconds")
        print(f"Total cumulative Insert time across all records: {total_insert_time_overall:.4f} seconds")
        print(f"Note: Individual insert times are averages derived from batch inserts.")

    print("\nProcessing complete.")

if __name__ == "__main__":
    try:
        import numpy as np
    except ImportError:
        print("NumPy not found. Please install it: pip install numpy")
        exit(1)

    main()
