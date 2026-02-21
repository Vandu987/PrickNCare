import 'package:get_it/get_it.dart';
import 'package:dio/dio.dart';
import '../constants/app_constants.dart';

final GetIt sl = GetIt.instance;

Future<void> configureDependencies() async {
  // Dio HTTP client
  sl.registerLazySingleton<Dio>(() {
    final dio = Dio(BaseOptions(
      baseUrl: AppConstants.baseUrl,
      connectTimeout: const Duration(milliseconds: AppConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: AppConstants.receiveTimeout),
      headers: {'Content-Type': 'application/json'},
    ));
    return dio;
  });
}
