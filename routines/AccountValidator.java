package routines;

import java.util.regex.Pattern;

/**
 * Account and identity validation utilities.
 * Used by: customer_extract, customer_validation, dedup_customer
 */
public class AccountValidator {

    private static final Pattern SSN_PATTERN = Pattern.compile("^\\d{3}-\\d{2}-\\d{4}$");
    private static final Pattern SSN_NUMERIC = Pattern.compile("^\\d{9}$");
    private static final Pattern ACCOUNT_PATTERN = Pattern.compile("^[A-Z]{2}\\d{10}$");

    /**
     * Validate SSN format (###-##-#### or #########).
     * Also rejects known invalid ranges (000, 666, 900-999 prefix).
     */
    public static boolean isValidSSN(String ssn) {
        if (ssn == null || ssn.trim().isEmpty()) return false;

        String cleaned = ssn.replaceAll("-", "");
        if (!SSN_NUMERIC.matcher(cleaned).matches()) return false;

        String area = cleaned.substring(0, 3);
        String group = cleaned.substring(3, 5);
        String serial = cleaned.substring(5, 9);

        if (area.equals("000") || area.equals("666") || area.startsWith("9")) return false;
        if (group.equals("00")) return false;
        if (serial.equals("0000")) return false;

        return true;
    }

    /**
     * Format SSN to standard ###-##-#### format.
     */
    public static String formatSSN(String ssn) {
        if (ssn == null) return null;
        String cleaned = ssn.replaceAll("[^0-9]", "");
        if (cleaned.length() != 9) return ssn;
        return cleaned.substring(0, 3) + "-" + cleaned.substring(3, 5) + "-" + cleaned.substring(5);
    }

    /**
     * Validate internal account number format (2 alpha + 10 digits).
     */
    public static boolean isValidAccountNumber(String accountNum) {
        if (accountNum == null) return false;
        return ACCOUNT_PATTERN.matcher(accountNum.trim().toUpperCase()).matches();
    }

    /**
     * Perform Luhn check on a numeric string (credit card, account validation).
     */
    public static boolean luhnCheck(String number) {
        if (number == null || number.isEmpty()) return false;
        String cleaned = number.replaceAll("[^0-9]", "");
        if (cleaned.isEmpty()) return false;

        int sum = 0;
        boolean alternate = false;
        for (int i = cleaned.length() - 1; i >= 0; i--) {
            int digit = Character.getNumericValue(cleaned.charAt(i));
            if (alternate) {
                digit *= 2;
                if (digit > 9) digit -= 9;
            }
            sum += digit;
            alternate = !alternate;
        }
        return sum % 10 == 0;
    }

    /**
     * Mask a sensitive field, showing only the last N characters.
     * Example: maskField("123-45-6789", 4) → "***-**-6789"
     */
    public static String maskField(String value, int showLast) {
        if (value == null || value.length() <= showLast) return value;
        StringBuilder masked = new StringBuilder();
        for (int i = 0; i < value.length() - showLast; i++) {
            masked.append(Character.isDigit(value.charAt(i)) ? '*' : value.charAt(i));
        }
        masked.append(value.substring(value.length() - showLast));
        return masked.toString();
    }
}
