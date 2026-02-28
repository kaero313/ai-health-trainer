import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/widgets/placeholder_screen.dart';
import 'main_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (c, s) => const PlaceholderScreen(title: 'Splash'),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (c, s) => const PlaceholderScreen(title: 'Onboarding'),
      ),
      GoRoute(
        path: '/login',
        builder: (c, s) => const PlaceholderScreen(title: 'Login'),
      ),
      GoRoute(
        path: '/register',
        builder: (c, s) => const PlaceholderScreen(title: 'Register'),
      ),
      ShellRoute(
        builder: (context, state, child) => MainShell(
          currentLocation: state.uri.path,
          child: child,
        ),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (c, s) => const PlaceholderScreen(title: 'Dashboard'),
          ),
          GoRoute(
            path: '/diet',
            builder: (c, s) => const PlaceholderScreen(title: 'Diet'),
          ),
          GoRoute(
            path: '/exercise',
            builder: (c, s) => const PlaceholderScreen(title: 'Exercise'),
          ),
          GoRoute(
            path: '/profile',
            builder: (c, s) => const PlaceholderScreen(title: 'Profile'),
          ),
        ],
      ),
      GoRoute(
        path: '/diet/analyze',
        builder: (c, s) => const PlaceholderScreen(title: 'Analyze'),
      ),
      GoRoute(
        path: '/diet/add',
        builder: (c, s) => const PlaceholderScreen(title: 'Diet Add'),
      ),
      GoRoute(
        path: '/diet/recommend',
        builder: (c, s) => const PlaceholderScreen(title: 'Diet Recommend'),
      ),
      GoRoute(
        path: '/exercise/add',
        builder: (c, s) => const PlaceholderScreen(title: 'Exercise Add'),
      ),
      GoRoute(
        path: '/exercise/recommend',
        builder: (c, s) => const PlaceholderScreen(title: 'Exercise Recommend'),
      ),
      GoRoute(
        path: '/exercise/history/:group',
        builder: (c, s) =>
            PlaceholderScreen(title: 'History ${s.pathParameters["group"]}'),
      ),
      GoRoute(
        path: '/profile/edit',
        builder: (c, s) => const PlaceholderScreen(title: 'Profile Edit'),
      ),
    ],
  );
});
