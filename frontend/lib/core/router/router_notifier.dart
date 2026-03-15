import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/domain/auth_state_provider.dart';
import '../../features/profile/domain/profile_check_provider.dart';

class RouterNotifier extends ChangeNotifier {
  final Ref _ref;

  RouterNotifier(this._ref) {
    _ref.listen<AsyncValue<AppAuthState>>(authStateProvider, (_, __) {
      notifyListeners();
    });
    _ref.listen<AsyncValue<bool>>(profileCheckProvider, (_, __) {
      notifyListeners();
    });
  }
}

final routerNotifierProvider = Provider<RouterNotifier>((ref) {
  final RouterNotifier notifier = RouterNotifier(ref);
  ref.onDispose(notifier.dispose);
  return notifier;
});
