package routines;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.NumberFormat;
import java.util.Locale;

/**
 * Currency and amount utilities for financial ETL processing.
 * Used by: loan_application_ingest, loan_risk_scoring, payment_match,
 *          payment_discrepancy, payment_settlement, cfpb_extract, occ_compliance_report
 */
public class AmountUtils {

    /**
     * Round a double to the specified number of decimal places.
     * Uses HALF_UP rounding (standard financial rounding).
     */
    public static double roundToDecimal(double value, int places) {
        BigDecimal bd = BigDecimal.valueOf(value);
        bd = bd.setScale(places, RoundingMode.HALF_UP);
        return bd.doubleValue();
    }

    /**
     * Format a numeric amount as US currency string.
     * Example: 45000.5 → "$45,000.50"
     */
    public static String formatCurrency(double amount) {
        NumberFormat fmt = NumberFormat.getCurrencyInstance(Locale.US);
        return fmt.format(amount);
    }

    /**
     * Calculate monthly payment using standard amortization formula.
     * P = L * [r(1+r)^n] / [(1+r)^n - 1]
     * where L = loan amount, r = monthly rate, n = number of months
     */
    public static double calculateMonthlyPayment(double loanAmount, double annualRate, int termMonths) {
        if (loanAmount <= 0 || termMonths <= 0) return 0;
        if (annualRate <= 0) return loanAmount / termMonths;

        double monthlyRate = annualRate / 100.0 / 12.0;
        double factor = Math.pow(1 + monthlyRate, termMonths);
        return roundToDecimal(loanAmount * (monthlyRate * factor) / (factor - 1), 2);
    }

    /**
     * Validate that an amount is positive and within acceptable range.
     * Used for input validation before loading to Snowflake.
     */
    public static boolean isValidAmount(double amount, double maxAllowed) {
        return amount > 0 && amount <= maxAllowed && !Double.isNaN(amount) && !Double.isInfinite(amount);
    }

    /**
     * Convert cents to dollars.
     */
    public static double centsToDollars(long cents) {
        return roundToDecimal(cents / 100.0, 2);
    }
}
