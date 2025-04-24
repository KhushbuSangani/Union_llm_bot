import os
import json,time
import zipfile
import schedule
from datetime import datetime
from pathlib import Path
from utils.db_connector import execute_query  

def backup_and_delete_conversations():
    today = datetime.today()
    year = today.year
    month = today.strftime("%B")  # Full month name (e.g., "February")

    # Ensure backup only runs on the 1st of the month
    if today.day != 1:
        return

    # # Fetch conversation records
    rows = execute_query("SELECT * FROM conversation", "select")

    # Convert rows to a list
    conversation_list = list(rows)

    if len(conversation_list) > 500:
        # Create backup directory structure: backup/{year}/
        
        # JSON file path (e.g., "backup/2025/February.json")
        current_year = datetime.now().strftime("%Y")
        current_month = datetime.now().strftime("%m")
        current_month_name = datetime.now().strftime("%B")

        # Define the path for the zip file that will hold all monthly backups for the year
        zip_file_path = Path(f"backup/{current_year}.zip")

        # Create a list to store all monthly JSON files
        json_files_in_zip = []

        # Convert datetime to string if necessary
        for conversation in conversation_list:
            if isinstance(conversation.get('timestamp'), datetime):
                # Convert datetime to string in a readable format (e.g., "YYYY-MM-DD HH:MM:SS")
                conversation['timestamp'] = conversation['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

        # Create a temporary JSON file in memory to represent this month's backup
        json_content = json.dumps(conversation_list, indent=4, ensure_ascii=False)

        # Create a zip file and add this month's data to it
        with zipfile.ZipFile(zip_file_path, "a", zipfile.ZIP_DEFLATED) as zipf:
            # Create a virtual file for this month's backup
            temp_json_filename = f"{current_month_name}.json"
            
            # Adding this month's JSON content to the zip file
            with zipf.open(temp_json_filename, "w") as temp_json_file:
                temp_json_file.write(json_content.encode('utf-8'))
            
            print(f"Added {temp_json_filename} to {zip_file_path}")

        print(f"Yearly backup zipped: {zip_file_path}")

        # Delete backed-up records from the database
        delete_query = """DELETE FROM conversation
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY timestamp DESC) AS rnum
                        FROM conversation
                    ) WHERE rnum > 500
                )"""
        execute_query(delete_query, "delete")

        print("Backed-up records deleted from the database.")

#schedule.every().day.at("00:00").do(backup_and_delete_conversations)
def run_scheduler():
    """This function runs the scheduler in a loop"""
    while True:
        schedule.run_pending()  # Run any scheduled tasks
        time.sleep(1)