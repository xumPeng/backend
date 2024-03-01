from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager
from django.utils.translation import gettext_lazy as _

# 定义用户信息模型
class NewUser(AbstractUser):

    role_type = [
        [0, 'admin'],
        [1, 'user'],
    ]

    roles = models.IntegerField(verbose_name="角色",choices=role_type,default=1)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True,auto_now=True)

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        verbose_name = "用户信息"
        verbose_name_plural = verbose_name  
        swappable = 'AUTH_USER_MODEL'

# 定义基础考核信息模型
class Assessment_Base(models.Model):
    file_name = models.CharField(max_length=100, null=True, blank=True)
    record_date = models.DateField(verbose_name="日期", null=True, blank=True)
    crew_group = models.CharField(max_length=50, verbose_name="班组", null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="姓名", null=True, blank=True)
    work_certificate_number = models.IntegerField(verbose_name="工作证编号", null=True, blank=True)
    train_model = models.CharField(max_length=20, verbose_name="车型", null=True, blank=True)
    assessment_item = models.CharField(max_length=100, verbose_name="考核项目", null=True, blank=True)
    # 考核结果的选择字段
    EXCELLENT = 3
    QUALIFIED = 2
    NOT_QUALIFIED = 1
    OTHER = 0  # 代表其他所有未知的考核结果
    ASSESSMENT_RESULTS = [
        (EXCELLENT, '优秀'),
        (QUALIFIED, '合格'),
        (NOT_QUALIFIED, '不合格'),
        (OTHER, '其他'),  # 允许有一个“其他”选项
    ]
    # 考核结果现在使用IntegerField来存储
    assessment_result = models.IntegerField(
        choices=ASSESSMENT_RESULTS,
        default=OTHER,  # 默认值设置为0，对应于“其他”
        verbose_name="考核结果"
    )
    # 动态数据字段存储整体用时和每个步骤的用时
    additional_data = models.JSONField(verbose_name="动态数据", blank=True, null=True)  # 用于存储额外的动态数据

    class Meta:
        verbose_name = "考核信息"
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        # 显示车型信息-文件名-姓名
        return f"{self.file_name} - {self.train_model} - {self.name}"

# 创建关联模型存储分类信息
class Assessment_Classification(models.Model):
    assessment_base = models.ForeignKey(Assessment_Base, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=100,verbose_name="文件名",default="default_file")
    data_key = models.CharField(max_length=255, verbose_name="数据键", default='default_key')  # 用于标识additional_data中的操作条目
    category = models.CharField(max_length=50,verbose_name="分类")  # 识故、排故、操作确认之一

    class Meta:
        verbose_name = "分类信息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.assessment_base.file_name}: {self.category}"