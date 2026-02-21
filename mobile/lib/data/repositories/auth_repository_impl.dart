import '../../domain/entities/user_entity.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_datasource.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource _remoteDataSource;

  AuthRepositoryImpl(this._remoteDataSource);

  @override
  Future<void> requestOtp(String phone) =>
      _remoteDataSource.requestOtp(phone);

  @override
  Future<UserEntity> verifyOtp(String phone, String otp) =>
      _remoteDataSource.verifyOtp(phone, otp);

  @override
  Future<void> logout() async {}

  @override
  Future<UserEntity?> getCurrentUser() async => null;
}
