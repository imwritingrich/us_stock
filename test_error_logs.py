import db_manager as db
import os

# Initialize database
db.init_db()

print("1. Simulating failed stock ingestion...")
ticker = "TEST_FAIL_TICKER"
error_msg = "ValueError: simulated data completeness error"
failed_at = "2026-05-22 17:30"

# Save to failed stocks table in DB
db.save_failed_stock(ticker, error_msg, failed_at)
print("Successfully saved simulated failure to database.")

# Log to physical log file
db.log_error_to_file(ticker, error_msg)
print("Successfully appended to sync_errors.log.")

# Check DB
failed_list = db.get_all_failed_stocks()
print("Failed stocks in DB:", failed_list)

# Check File
if os.path.exists("sync_errors.log"):
    print("sync_errors.log exists! File contents:")
    with open("sync_errors.log", "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("sync_errors.log does not exist!")

# Cleanup DB test row
db.delete_failed_stock(ticker)
print("Cleaned up simulated test row from DB.")
