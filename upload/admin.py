from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.forms import TextInput
from django.utils.translation import gettext_lazy as _

from .models import NewUser, Assessment_Base, Assessment_Classification

# 创建NewUser模型的admin类
class NewUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email','first_name','last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions','roles',)}),
        (_('Important dates'), {'fields': ('date_joined',)}),
    )

    list_display = ('id','username', 'roles', 'email', 'is_active','last_login')
    list_display_links = ('id','username','roles','email','last_login')
    search_fields = ('username', 'email')

# 创建Assessment_Base模型的admin类
class AssessmentBaseAdmin(admin.ModelAdmin):
    # 设置整数型字段的输入框大小
    formfield_overrides = {
        models.IntegerField: {'widget': TextInput(attrs={'size':'20'})},
    }
    # 设置显示字段
    list_display = ('id','file_name','record_date','crew_group','name','train_model','assessment_item','assessment_result')
    list_display_links = ('id','record_date','crew_group','name','train_model','assessment_item','assessment_result','file_name')
    search_fields = ('record_date','crew_group','name','train_model','assessment_item','assessment_result','file_name')

# 创建Assessment_Classification模型的admin类
class AssessmentClassificationAdmin(admin.ModelAdmin):
    # 可以自定义这个类来满足你的需要，比如定义list_display来显示特定的字段
    list_display = ('assessment_base','file_name','data_key','category')
    list_display_links = ('assessment_base','file_name','data_key','category')
    search_fields = ('assessment_base__file_name','data_key','category')  # 允许通过file_name和category搜索

# 在管理员后台注册模型
admin.site.register(NewUser,NewUserAdmin)
admin.site.register(Assessment_Base, AssessmentBaseAdmin)
admin.site.register(Assessment_Classification, AssessmentClassificationAdmin)