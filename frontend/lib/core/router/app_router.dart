import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/auth_state_provider.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/onboarding_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/chat/presentation/chat_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/dashboard/presentation/monthly_report_screen.dart';
import '../../features/diet/presentation/diet_add_screen.dart';
import '../../features/diet/presentation/diet_analyze_screen.dart';
import '../../features/diet/presentation/diet_recommend_screen.dart';
import '../../features/diet/presentation/diet_screen.dart';
import '../../features/exercise/presentation/exercise_add_screen.dart';
import '../../features/exercise/presentation/exercise_recommend_screen.dart';
import '../../features/exercise/presentation/exercise_screen.dart';
import '../../features/profile/domain/profile_check_provider.dart';
import '../../features/profile/presentation/profile_edit_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
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
      final bool isProfileEditRoute = path == '/profile/edit';

      return authAsync.when(
        loading: () => null,
        error: (_, __) => path == '/login' ? null : '/login',
        data: (AppAuthState authState) {
          final bool isAuthenticated = authState == AppAuthState.authenticated;

          // 미인증 -> 로그인 페이지로
          if (!isAuthenticated && !isAuthRoute) {
            return '/login';
          }

          // 인증됨 + auth 라우트(splash 제외) -> 대시보드로
          if (isAuthenticated && isAuthRoute && path != '/splash') {
            return '/dashboard';
          }

          // 인증됨 + 프로필 편집 중 -> 리다이렉트 안 함
          if (isAuthenticated && isProfileEditRoute) {
            return null;
          }

          // 인증됨 + 프로필 체크
          if (isAuthenticated && !isAuthRoute) {
            final AsyncValue<bool> profileAsync = ref.read(profileCheckProvider);
            return profileAsync.when(
              loading: () => null,
              error: (_, __) => null,
              data: (bool hasProfile) {
                if (!hasProfile) {
                  return '/profile/edit';
                }
                return null;
              },
            );
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
      GoRoute(
        path: '/ai/chat',
        pageBuilder:
            (c, s) => _buildTransitionPage(state: s, child: const ChatScreen()),
      ),
      ShellRoute(
        builder:
            (context, state, child) =>
                MainShell(currentLocation: state.uri.path, child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (c, s) => const DashboardScreen(),
            routes: [
              GoRoute(
                path: 'monthly',
                pageBuilder:
                    (c, s) => _buildTransitionPage(
                      state: s,
                      child: const MonthlyReportScreen(),
                    ),
              ),
            ],
          ),
          GoRoute(path: '/diet', builder: (c, s) => const DietScreen()),
          GoRoute(path: '/exercise', builder: (c, s) => const ExerciseScreen()),
          GoRoute(path: '/profile', builder: (c, s) => const ProfileScreen()),
        ],
      ),
      GoRoute(
        path: '/diet/analyze',
        pageBuilder:
            (c, s) => _buildTransitionPage(
              state: s,
              child: const DietAnalyzeScreen(),
            ),
      ),
      GoRoute(
        path: '/diet/add',
        pageBuilder:
            (c, state) => _buildTransitionPage(
              state: state,
              child: DietAddScreen(
                mealType: state.uri.queryParameters['meal_type'],
              ),
            ),
      ),
      GoRoute(
        path: '/diet/recommend',
        pageBuilder:
            (c, s) => _buildTransitionPage(
              state: s,
              child: const DietRecommendScreen(),
            ),
      ),
      GoRoute(
        path: '/exercise/add',
        pageBuilder: (c, s) {
          final Map<String, dynamic>? extraMap = _readExtraMap(s.extra);
          return _buildTransitionPage(
            state: s,
            child: ExerciseAddScreen(
              exerciseName: _readString(extraMap, 'exercise_name'),
              muscleGroup: _readString(extraMap, 'muscle_group'),
              sets: _readInt(extraMap, 'sets'),
              reps: _readInt(extraMap, 'reps'),
              weightKg: _readDouble(extraMap, 'weight_kg'),
            ),
          );
        },
      ),
      GoRoute(
        path: '/exercise/recommend',
        pageBuilder:
            (c, s) => _buildTransitionPage(
              state: s,
              child: const ExerciseRecommendScreen(),
            ),
      ),
      GoRoute(
        path: '/profile/edit',
        pageBuilder:
            (c, s) => _buildTransitionPage(
              state: s,
              child: const ProfileEditScreen(),
            ),
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

CustomTransitionPage<void> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 300),
    transitionsBuilder: (
      BuildContext context,
      Animation<double> animation,
      Animation<double> secondaryAnimation,
      Widget child,
    ) {
      final CurvedAnimation curvedAnimation = CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
      );
      final Animation<Offset> slideAnimation = Tween<Offset>(
        begin: const Offset(0, 0.1),
        end: Offset.zero,
      ).animate(curvedAnimation);
      final Animation<double> fadeAnimation = Tween<double>(
        begin: 0,
        end: 1,
      ).animate(curvedAnimation);

      return FadeTransition(
        opacity: fadeAnimation,
        child: SlideTransition(position: slideAnimation, child: child),
      );
    },
  );
}
