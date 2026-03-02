import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/chat_repository.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen>
    with SingleTickerProviderStateMixin {
  final List<Map<String, Object?>> _messages = <Map<String, Object?>>[];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  late final AnimationController _typingController;
  bool _isLoading = false;
  String _contextType = 'general';

  static const List<String> _contextOrder = <String>[
    'general',
    'diet',
    'exercise',
  ];

  static const Map<String, String> _contextLabels = <String, String>{
    'general': '전체',
    'diet': '🍽 식단',
    'exercise': '💪 운동',
  };

  @override
  void initState() {
    super.initState();
    _typingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();

    _messages.add(
      _buildMessage(
        role: 'assistant',
        text: '안녕하세요! AI 코칭 도우미입니다. 식단, 운동, 건강에 대해 무엇이든 물어보세요. 🤖',
      ),
    );
  }

  @override
  void dispose() {
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  bool get _canSend => _textController.text.trim().isNotEmpty && !_isLoading;

  InputDecoration _inputDecoration() {
    return InputDecoration(
      hintText: '질문을 입력하세요',
      hintStyle: AppTypography.body2.copyWith(color: AppColors.textSecondary),
      filled: true,
      fillColor: AppColors.surfaceLight,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.md,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.divider),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.2),
      ),
    );
  }

  Map<String, Object?> _buildMessage({
    required String role,
    required String text,
    List<String>? sources,
  }) {
    return <String, Object?>{
      'role': role,
      'text': text,
      'sources': sources,
      'timestamp': DateTime.now(),
    };
  }

  Future<void> _sendMessage() async {
    final String userText = _textController.text.trim();
    if (userText.isEmpty || _isLoading) {
      return;
    }

    setState(() {
      _messages.add(_buildMessage(role: 'user', text: userText));
      _textController.clear();
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final Map<String, dynamic> data = await ref
          .read(chatRepositoryProvider)
          .sendMessage(userText, _contextType);

      final String answer = (data['answer']?.toString() ?? '').trim();
      final List<String> sources =
          (data['sources'] as List<dynamic>? ?? <dynamic>[])
              .map((dynamic item) => item.toString())
              .where((String item) => item.isNotEmpty)
              .toList();

      setState(() {
        _messages.add(
          _buildMessage(
            role: 'assistant',
            text: answer.isEmpty ? '응답을 받지 못했습니다' : answer,
            sources: sources.isEmpty ? null : sources,
          ),
        );
      });
    } catch (e) {
      setState(() {
        _messages.add(
          _buildMessage(
            role: 'assistant',
            text: '죄송합니다. ${_extractErrorMessage(e)}',
          ),
        );
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        _scrollToBottom();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('AI 코칭')),
      body: SafeArea(
        child: Column(
          children: [
            _ContextTypeChips(
              selectedContext: _contextType,
              contextOrder: _contextOrder,
              contextLabels: _contextLabels,
              onSelected: (String contextType) {
                setState(() {
                  _contextType = contextType;
                });
              },
            ),
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.all(AppSpacing.md),
                itemCount: _messages.length + (_isLoading ? 1 : 0),
                itemBuilder: (BuildContext context, int index) {
                  if (_isLoading && index == _messages.length) {
                    return _TypingMessage(animation: _typingController);
                  }
                  final Map<String, Object?> message = _messages[index];
                  return _ChatMessageItem(message: message);
                },
              ),
            ),
            Container(
              color: AppColors.surface,
              padding: const EdgeInsets.all(AppSpacing.md),
              child: SafeArea(
                top: false,
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _textController,
                        minLines: 1,
                        maxLines: 4,
                        style: AppTypography.body1,
                        decoration: _inputDecoration(),
                        onChanged: (_) => setState(() {}),
                        onSubmitted: (_) => _sendMessage(),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    CircleAvatar(
                      radius: 22,
                      backgroundColor:
                          _canSend ? AppColors.primary : AppColors.divider,
                      child: IconButton(
                        onPressed: _canSend ? _sendMessage : null,
                        icon: Icon(
                          Icons.send,
                          color:
                              _canSend
                                  ? AppColors.background
                                  : AppColors.textSecondary,
                          size: 20,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContextTypeChips extends StatelessWidget {
  final String selectedContext;
  final List<String> contextOrder;
  final Map<String, String> contextLabels;
  final ValueChanged<String> onSelected;

  const _ContextTypeChips({
    required this.selectedContext,
    required this.contextOrder,
    required this.contextLabels,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 52,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: Row(
          children: [
            for (final String contextType in contextOrder) ...[
              ChoiceChip(
                label: Text(contextLabels[contextType] ?? contextType),
                selected: selectedContext == contextType,
                selectedColor: AppColors.primary,
                backgroundColor: AppColors.surface,
                side: BorderSide(
                  color:
                      selectedContext == contextType
                          ? AppColors.primary
                          : AppColors.divider,
                ),
                labelStyle: AppTypography.caption.copyWith(
                  color:
                      selectedContext == contextType
                          ? AppColors.background
                          : AppColors.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
                onSelected: (_) => onSelected(contextType),
              ),
              const SizedBox(width: AppSpacing.xs),
            ],
          ],
        ),
      ),
    );
  }
}

class _ChatMessageItem extends StatelessWidget {
  final Map<String, Object?> message;

  const _ChatMessageItem({required this.message});

  @override
  Widget build(BuildContext context) {
    final String role = message['role']?.toString() ?? 'assistant';
    final String text = message['text']?.toString() ?? '';
    final List<String> sources =
        (message['sources'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic item) => item.toString())
            .where((String item) => item.isNotEmpty)
            .toList();

    if (role == 'user') {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Text(
            text,
            style: AppTypography.body2.copyWith(color: AppColors.textPrimary),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.surfaceLight,
            child: Text('🤖', style: TextStyle(fontSize: 12)),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DecoratedBox(
                  decoration: glassCardDecoration,
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    child: Text(text, style: AppTypography.body2),
                  ),
                ),
                if (sources.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.xs),
                  for (final String source in sources)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                      child: Text(
                        '📚 $source',
                        style: AppTypography.caption.copyWith(
                          color: AppColors.info,
                        ),
                      ),
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TypingMessage extends StatelessWidget {
  final AnimationController animation;

  const _TypingMessage({required this.animation});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.surfaceLight,
            child: Text('🤖', style: TextStyle(fontSize: 12)),
          ),
          const SizedBox(width: AppSpacing.sm),
          DecoratedBox(
            decoration: glassCardDecoration,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: AppSpacing.sm,
              ),
              child: AnimatedBuilder(
                animation: animation,
                builder: (BuildContext context, Widget? child) {
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List<Widget>.generate(3, (int index) {
                      return Container(
                        margin: EdgeInsets.only(
                          right: index == 2 ? 0 : AppSpacing.xs,
                        ),
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: AppColors.textSecondary.withValues(
                            alpha: _dotOpacity(animation.value, index),
                          ),
                          shape: BoxShape.circle,
                        ),
                      );
                    }),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  double _dotOpacity(double progress, int index) {
    const double segment = 1 / 3;
    final double start = index * segment;
    final double end = start + segment;
    if (progress < start || progress > end) {
      return 0.3;
    }
    final double local = (progress - start) / segment;
    final double wave = 1 - (2 * local - 1).abs();
    return 0.3 + (0.7 * wave);
  }
}

String _extractErrorMessage(Object error) {
  if (error is ChatRepositoryException) {
    return error.message;
  }
  return error.toString();
}
