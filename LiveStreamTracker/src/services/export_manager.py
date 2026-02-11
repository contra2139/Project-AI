import csv
import openpyxl
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class ExportManager:
    """
    Manages exporting data to CSV and Excel.
    """
    def __init__(self, export_dir="exports"):
        self.export_dir = export_dir
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

    def export_to_csv(self, data, filename_prefix="report"):
        """Exports a list of lists to CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            logger.info(f"Exported CSV to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return None

    def export_to_excel(self, data, filename_prefix="report"):
        """Exports a list of lists to Excel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.xlsx"
        filepath = os.path.join(self.export_dir, filename)

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            for row in data:
                ws.append(row)
            wb.save(filepath)
            logger.info(f"Exported Excel to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export Excel: {e}")
            return None
