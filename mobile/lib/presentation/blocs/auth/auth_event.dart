part of 'auth_bloc.dart';

abstract class AuthEvent {}

class AuthOtpRequested extends AuthEvent {
  final String phone;
  AuthOtpRequested(this.phone);
}

class AuthOtpVerified extends AuthEvent {
  final String phone;
  final String otp;
  AuthOtpVerified(this.phone, this.otp);
}

class AuthLoggedOut extends AuthEvent {}
