import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/auth_state_provider.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/onboarding_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/diet/presentation/diet_add_screen.dart';
import '../../features/diet/presentation/diet_screen.dart';
import '../../features/exercise/presentation/exercise_add_screen.dart';
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
        builder: (c, s) => const PlaceholderScreen(title: 'Analyze'),
      ),
      GoRoute(
        path: '/diet/add',
        builder:
            (c, state) =>
                DietAddScreen(mealType: state.uri.queryParameters['meal_type']),
      ),
      GoRoute(
        path: '/diet/recommend',
        builder: (c, s) => const PlaceholderScreen(title: 'Diet Recommend'),
      ),
      GoRoute(
        path: '/exercise/add',
        builder: (c, s) => const ExerciseAddScreen(),
      ),
      GoRoute(
        path: '/exercise/recommend',
        builder: (c, s) => const PlaceholderScreen(title: 'Exercise Recommend'),
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
