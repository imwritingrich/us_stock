import sqlite3
import os
from typing import Dict, List, Any, Optional

DEFAULT_DB_PATH = "stocks.db"

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database tables and inserts default settings."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Create Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # 2. Check and migrate Stocks table if old indicators exist without losing data
    try:
        cursor.execute("PRAGMA table_info(stocks)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and any(col in columns for col in ["ma50", "ma200", "rsi"]):
            # Create a temporary table with the new schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks_temp (
                    ticker TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    industry TEXT,
                    price REAL,
                    recommendation TEXT,
                    weight TEXT,
                    analysis_date TEXT,
                    raw_analysis TEXT,
                    pe REAL,
                    peg REAL,
                    pb REAL,
                    roe REAL,
                    comprehensive_report TEXT
                )
            """)
            
            # Copy existing data to the temporary table (only columns that we keep)
            cursor.execute("""
                INSERT INTO stocks_temp (
                    ticker, name, sector, industry, price, 
                    recommendation, weight, analysis_date, raw_analysis,
                    pe, peg, pb, roe
                )
                SELECT 
                    ticker, name, sector, industry, price, 
                    recommendation, weight, analysis_date, raw_analysis,
                    pe, peg, pb, roe 
                FROM stocks
            """)
            
            # Drop the old table
            cursor.execute("DROP TABLE stocks")
            
            # Rename the temporary table to stocks
            cursor.execute("ALTER TABLE stocks_temp RENAME TO stocks")
            
            # Commit migration
            conn.commit()
            
        # Migrate table to add comprehensive_report if it's missing in an existing database
        cursor.execute("PRAGMA table_info(stocks)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "comprehensive_report" not in columns:
            cursor.execute("ALTER TABLE stocks ADD COLUMN comprehensive_report TEXT")
            conn.commit()
            
    except Exception as e:
        print(f"Error migrating database table stocks: {e}")

    # Create Stocks table (without ma50, ma200, rsi) if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            industry TEXT,
            price REAL,
            recommendation TEXT,
            weight TEXT,
            analysis_date TEXT,
            raw_analysis TEXT,
            pe REAL,
            peg REAL,
            pb REAL,
            roe REAL,
            comprehensive_report TEXT
        )
    """)
    
    # 2.5 Create Failed Stocks table for error logging
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_stocks (
            ticker TEXT PRIMARY KEY,
            error_message TEXT,
            failed_at TEXT
        )
    """)
    
    # 3. Insert default settings (with INSERT OR IGNORE to prevent overwriting user edits)
    default_settings = [
        ("gemini_api_key", ""),
        ("google_sheet_url", "https://docs.google.com/spreadsheets/d/1PSYb9wyqXkRZT8NJtna9749Fqb_Pb8mPxZITmKLXTuA/edit?usp=drive_link"),
        ("gemini_model", "gemini-2.5-flash")
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
        default_settings
    )
    
    conn.commit()
    conn.close()

def get_setting(key: str, default: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> Optional[str]:
    """Retrieves a setting value by key."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row["value"]
    return default

def set_setting(key: str, value: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Sets/updates a setting value."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
        (key, value)
    )
    conn.commit()
    conn.close()

def get_all_stocks(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all stock analyses from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks ORDER BY ticker ASC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_stock(ticker: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves analysis for a single stock by ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker.upper(),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def save_stock(stock_data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Saves or updates stock details and analysis in the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    fields = [
        "ticker", "name", "sector", "industry", "price", 
        "recommendation", "weight", "analysis_date", "raw_analysis",
        "pe", "peg", "pb", "roe", "comprehensive_report"
    ]
    
    placeholders = ", ".join(["?"] * len(fields))
    columns = ", ".join(fields)
    
    # Extract values in the correct order, default to None if missing
    values = [stock_data.get(field) for field in fields]
    
    # Capitalize the ticker to ensure consistency
    if values[0]:
        values[0] = values[0].upper()
        
    cursor.execute(
        f"INSERT OR REPLACE INTO stocks ({columns}) VALUES ({placeholders})",
        values
    )
    
    conn.commit()
    conn.close()

def clear_stocks(db_path: str = DEFAULT_DB_PATH) -> None:
    """Deletes all stock analyses from the database (settings are preserved)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stocks")
    conn.commit()
    conn.close()

def save_failed_stock(ticker: str, error_message: str, failed_at: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Saves or updates a failed stock sync error log in the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO failed_stocks (ticker, error_message, failed_at) VALUES (?, ?, ?)",
        (ticker.upper(), error_message, failed_at)
    )
    conn.commit()
    conn.close()

def delete_failed_stock(ticker: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Removes a stock from the failed stocks table if it has been successfully analyzed."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM failed_stocks WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()

def get_all_failed_stocks(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all failed stock sync error logs from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM failed_stocks ORDER BY failed_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_failed_stocks(db_path: str = DEFAULT_DB_PATH) -> None:
    """Clears all failed stock logs from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM failed_stocks")
    conn.commit()
    conn.close()

def log_error_to_file(ticker: str, error_message: str) -> None:
    """Appends a detailed error log into sync_errors.log in the project directory."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] TICKER: {ticker.upper()} | ERROR: {error_message}\n"
    try:
        with open("sync_errors.log", "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to write log to file: {e}")

# Test database initialization if executed directly
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    print("Default Sheet:", get_setting("google_sheet_url"))
    print("Default Model:", get_setting("gemini_model"))
