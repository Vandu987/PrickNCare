import 'package:intl/intl.dart';

class AppUtils {
  static String formatDate(DateTime date) =>
      DateFormat('dd MMM yyyy').format(date);

  static String formatTime(DateTime time) =>
      DateFormat('hh:mm a').format(time);

  static String formatCurrency(double amount) =>
      NumberFormat.currency(locale: 'en_IN', symbol: '₹').format(amount);

  static bool isValidPhone(String phone) =>
      RegExp(r'^\+91[6-9]\d{9}$').hasMatch(phone);

  static bool isValidOtp(String otp) =>
      RegExp(r'^\d{6}$').hasMatch(otp);
}
