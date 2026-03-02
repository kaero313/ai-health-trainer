import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/auth_state_provider.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/onboarding_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/diet/presentation/diet_add_screen.dart';
import '../../features/diet/presentation/diet_analyze_screen.dart';
import '../../features/diet/presentation/diet_recommend_screen.dart';
import '../../features/diet/presentation/diet_screen.dart';
import '../../features/exercise/presentation/exercise_add_screen.dart';
import '../../features/exercise/presentation/exercise_recommend_screen.dart';
import '../../features/exercise/presentation/exercise_screen.dart';
import '../../features/profile/presentation/profile_edit_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
import '../../shared/widgets/placeholder_screen.dart';
import 'main_shell.dart';
import 'router_notifier.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final RouterNotifier notifier = ref.read(routerNotifierProvider);
  final GoRouter router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: notifier,
    redirect: (context, state) {
      final AsyncValue<AppAuthState> authAsync = ref.read(authStateProvider);
      final String path = state.uri.path;
      final bool isAuthRoute = <String>{
        '/login',
        '/register',
        '/splash',
        '/onboarding',
      }.contains(path);

      return authAsync.when(
        loading: () => null,
        error: (_, __) => path == '/login' ? null : '/login',
        data: (AppAuthState authState) {
          final bool isAuthenticated = authState == AppAuthState.authenticated;

          if (!isAuthenticated && !isAuthRoute) {
            return '/login';
          }

          if (isAuthenticated && isAuthRoute && path != '/splash') {
            return path == '/dashboard' ? null : '/dashboard';
          }

          return null;
        },
      );
    },
    routes: [
      GoRoute(path: '/splash', builder: (c, s) => const SplashScreen()),
      GoRoute(path: '/onboarding', builder: (c, s) => const OnboardingScreen()),
      GoRoute(path: '/login', builder: (c, s) => const LoginScreen()),
      GoRoute(path: '/register', builder: (c, s) => const RegisterScreen()),
      ShellRoute(
        builder:
            (context, state, child) =>
                MainShell(currentLocation: state.uri.path, child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (c, s) => const DashboardScreen(),
          ),
          GoRoute(path: '/diet', builder: (c, s) => const DietScreen()),
          GoRoute(path: '/exercise', builder: (c, s) => const ExerciseScreen()),
          GoRoute(path: '/profile', builder: (c, s) => const ProfileScreen()),
        ],
      ),
      GoRoute(
        path: '/diet/analyze',
        builder: (c, s) => const DietAnalyzeScreen(),
      ),
      GoRoute(
        path: '/diet/add',
        builder:
            (c, state) =>
                DietAddScreen(mealType: state.uri.queryParameters['meal_type']),
      ),
      GoRoute(
        path: '/diet/recommend',
        builder: (c, s) => const DietRecommendScreen(),
      ),
      GoRoute(
        path: '/exercise/add',
        builder: (c, s) {
          final Map<String, dynamic>? extraMap = _readExtraMap(s.extra);
          return ExerciseAddScreen(
            exerciseName: _readString(extraMap, 'exercise_name'),
            muscleGroup: _readString(extraMap, 'muscle_group'),
            sets: _readInt(extraMap, 'sets'),
            reps: _readInt(extraMap, 'reps'),
            weightKg: _readDouble(extraMap, 'weight_kg'),
          );
        },
      ),
      GoRoute(
        path: '/exercise/recommend',
        builder: (c, s) => const ExerciseRecommendScreen(),
      ),
      GoRoute(
        path: '/exercise/history/:group',
        builder:
            (c, s) => PlaceholderScreen(
              title: 'History ${s.pathParameters["group"]}',
            ),
      ),
      GoRoute(
        path: '/profile/edit',
        builder: (c, s) => const ProfileEditScreen(),
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

Map<String, dynamic>? _readExtraMap(Object? extra) {
  if (extra is Map<String, dynamic>) {
    return extra;
  }
  if (extra is Map) {
    return extra.map(
      (dynamic key, dynamic value) =>
          MapEntry<String, dynamic>(key.toString(), value),
    );
  }
  return null;
}

String? _readString(Map<String, dynamic>? map, String key) {
  if (map == null) {
    return null;
  }
  final dynamic value = map[key];
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  if (text.isEmpty) {
    return null;
  }
  return text;
}

int? _readInt(Map<String, dynamic>? map, String key) {
  if (map == null) {
    return null;
  }
  final dynamic value = map[key];
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value.trim());
  }
  return null;
}

double? _readDouble(Map<String, dynamic>? map, String key) {
  if (map == null) {
    return null;
  }
  final dynamic value = map[key];
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value.trim());
  }
  return null;
}
