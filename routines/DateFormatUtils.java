package routines;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;

/**
 * Custom date formatting utilities for ETL processing.
 * Used by: customer_dimension_load, cfpb_extract, regulatory_archive
 */
public class DateFormatUtils {

    /**
     * Parse a date string with the given format pattern.
     * Returns null if the input is null or empty.
     */
    public static Date parseDate(String dateStr, String pattern) {
        if (dateStr == null || dateStr.trim().isEmpty()) {
            return null;
        }
        try {
            SimpleDateFormat sdf = new SimpleDateFormat(pattern);
            sdf.setLenient(false);
            return sdf.parse(dateStr.trim());
        } catch (ParseException e) {
            throw new RuntimeException("Failed to parse date '" + dateStr + "' with pattern '" + pattern + "'", e);
        }
    }

    /**
     * Format a date to the specified output pattern.
     * Returns empty string if date is null.
     */
    public static String formatDate(Date date, String pattern) {
        if (date == null) {
            return "";
        }
        SimpleDateFormat sdf = new SimpleDateFormat(pattern);
        return sdf.format(date);
    }

    /**
     * Convert a date string from one format to another.
     * Example: convertDateFormat("2024-01-15", "yyyy-MM-dd", "MM/dd/yyyy") → "01/15/2024"
     */
    public static String convertDateFormat(String dateStr, String fromPattern, String toPattern) {
        Date d = parseDate(dateStr, fromPattern);
        return d != null ? formatDate(d, toPattern) : "";
    }

    /**
     * Get the fiscal quarter for a given date.
     * FY starts in October: Oct-Dec=Q1, Jan-Mar=Q2, Apr-Jun=Q3, Jul-Sep=Q4
     */
    public static String getFiscalQuarter(Date date) {
        if (date == null) return null;
        SimpleDateFormat monthFormat = new SimpleDateFormat("MM");
        int month = Integer.parseInt(monthFormat.format(date));
        SimpleDateFormat yearFormat = new SimpleDateFormat("yyyy");
        int year = Integer.parseInt(yearFormat.format(date));

        if (month >= 10) return "Q1-FY" + (year + 1);
        if (month >= 7) return "Q4-FY" + year;
        if (month >= 4) return "Q3-FY" + year;
        return "Q2-FY" + year;
    }
}
