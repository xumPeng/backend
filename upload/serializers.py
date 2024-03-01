from rest_framework import serializers
from .models import Assessment_Base, Assessment_Classification

# 考核信息序列化器
class AssessmentBaseSerializer(serializers.ModelSerializer):
    # 添加一个新的字段trainLines, 这个字段不在模型中定义，而是动态计算得到
    """
    A read-only field that get its representation from calling a method on the
    parent serializer class. The method called will be of the form
    "get_{field_name}", and should take a single argument, which is the
    object being serialized.

    For example:

    class ExampleSerializer(self):
        extra_info = SerializerMethodField()

        def get_extra_info(self, obj):
            return ...  # Calculate some data to return.
    """
    trainLines = serializers.SerializerMethodField()

    class Meta:
        model = Assessment_Base
        fields = '__all__'  # 确保包含所有模型字段以及新添加的trainLines字段

    # 定义一个方法来获取train_model字段的前两位 即线路编号
    def get_trainLines(self, obj):
        # 如果train_model字段存在且长度大于等于2, 则返回其前两位
        if obj.train_model and len(obj.train_model) >= 2:
            return obj.train_model[:2]
        return None  # 如果条件不满足，返回None或者一个默认值
    
# 分类信息序列化器
class AssessmentClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment_Classification
        fields = '__all__'