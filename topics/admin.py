from django.contrib import admin
from .models import (Interest, StudentInterest, Question, Option, OptionInterest,
                     GenerationSession, GeneratedTopic, AgentMessage)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class OptionInterestInline(admin.TabularInline):
    model = OptionInterest
    extra = 1


class GeneratedTopicInline(admin.TabularInline):
    model = GeneratedTopic
    extra = 0


class AgentMessageInline(admin.TabularInline):
    model = AgentMessage
    extra = 0


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    list_filter = ('category',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(StudentInterest)
class StudentInterestAdmin(admin.ModelAdmin):
    list_display = ('student', 'interest', 'weight', 'source')
    list_filter = ('source',)
    search_fields = ('student__username', 'interest__name')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'order')
    inlines = [OptionInline]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question')
    search_fields = ('text',)
    inlines = [OptionInterestInline]


@admin.register(GenerationSession)
class GenerationSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'specialty', 'institution_type', 'work_type', 'rounds', 'status', 'student', 'created_at')
    list_filter = ('institution_type', 'work_type', 'status')
    search_fields = ('specialty', 'student__username')
    inlines = [GeneratedTopicInline, AgentMessageInline]


@admin.register(GeneratedTopic)
class GeneratedTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'session', 'score', 'is_selected', 'is_pinned', 'round')
    list_filter = ('is_selected', 'is_pinned', 'round')
    search_fields = ('title',)


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'agent', 'provider', 'sequence_number', 'created_at')
    list_filter = ('agent',)