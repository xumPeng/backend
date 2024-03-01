import io
import operator
import re
from datetime import datetime
from functools import reduce

import pandas as pd
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import NewUser, Assessment_Base, Assessment_Classification
from .serializers import AssessmentBaseSerializer, AssessmentClassificationSerializer

# 获取当前登录用户信息
class UserInfoViewSet(viewsets.ViewSet):
    queryset = NewUser.objects.all().order_by('-date_joined')
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        # 由于已经登录了，所以request.user肯定是有值的，访问当前登录的用户的id
        user_info = NewUser.objects.filter(id=request.user.id).values().first()

        if user_info:
            role = request.user.roles
            user_info['roles'] = 'admin' if role == 0 else 'user'
            return Response(user_info)
        else:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

# 定义用户登出视图        
class LogoutView(APIView):

    def post(self, request):
        try:
            # 从请求中获取refresh_token
            refresh_token = request.data.get("refresh_token")
            # 如果refresh_token存在，就将其加入黑名单
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # 黑名单化 refresh_token
            # 返回205状态码
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as error:
            # 如果出错，打印错误信息
            print(error)
            return Response(status=status.HTTP_400_BAD_REQUEST)
# 上述两个CBV视图是用来获取当前登录用户信息和用户登出的，通用于所有的Django项目

# 定义文件上传并写入数据库的逻辑
class AssessmentUploadView(APIView):
    
    # 定义一个方法来将考核结果文本映射为整数存入数据库
    def map_assessment_result(self, result_text):
        mapping = {
            '优秀': Assessment_Base.EXCELLENT,
            '合格': Assessment_Base.QUALIFIED,
            '不合格': Assessment_Base.NOT_QUALIFIED,
        }
        return mapping.get(result_text, Assessment_Base.OTHER)    
    
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('file')

        for file_obj in files:
            try:
                with transaction.atomic():
                    file_name = file_obj.name
                    # 删除数据库中已有的同名文件的数据
                    Assessment_Base.objects.filter(file_name=file_name).delete()

                    file_content = file_obj.read()
                    df = None
                    '''
                    'latin1' (或 'iso-8859-1')：西欧语言字符集，是很多西欧语言的标准编码。
                    'ascii'：美国标准信息交换码，只能表示基本的英文字符和一些控制字符。
                    'utf-16'：与UTF-8类似，但使用至少16位（2字节）来编码字符，适用于编码较多的字符集。
                    'utf-32'：使用32位（4字节）来编码字符，与UTF-16类似，但更占用空间，用于需要编码非常多字符的情况。
                    'cp1252'：Windows的西欧字符集，与ISO-8859-1类似，但包含了一些在ISO-8859-1中未定义的打印字符。
                    'gb2312'：简体中文字符集，比GBK和GB18030早，但字符数量较少。
                    'big5'：繁体中文字符集，用于台湾、香港等地区的中文编码。
                    '''
                    for encoding in ['utf-8', 'gbk', 'latin1', 'ascii', 'utf-16', 'utf-32', 'cp1252', 'gb2312', 'big5']:
                        try:
                            io_string = io.StringIO(file_content.decode(encoding))
                            # 后续在这里会判断文件的格式，对于不同的文件格式，需要使用不同的方法来读取文件
                            # 例如：如果文件是csv格式，使用pd.read_csv方法来读取文件
                            # 如果文件是excel格式，使用pd.read_excel方法来读取文件
                            df = pd.read_csv(io_string, header=1)
                            break
                        except UnicodeDecodeError:
                            continue

                    if df is None:
                        return Response({'detail': f'文件 {file_name} 无法解码，请检查文件编码格式!'}, status=status.HTTP_400_BAD_REQUEST)

                    if '备注' in df.columns:
                        df = df.drop('备注', axis=1)
                    '''
                    科目的定义：09A02逃生门释放和收回
                    单科目单人重复填写，只保留最后一次的记录
                    通过按照 姓名、工作证编号、车型 和 考核项目 这几个关键字段排序
                    确保任何具有相同姓名、工作证编号、车型和考核项目的重复记录都会被排列在一起
                    先排序确保重复记录紧密排列，然后只保留最后出现的记录，这样做可以有效地处理数据中的重复项
                    '''   
                    df = df.sort_values(by=['姓名', '工作证编号', '车型', '考核项目'])
                    df = df.drop_duplicates(subset=['姓名', '工作证编号', '车型', '考核项目'], keep='last')
                    
                    # 首先，获取DataFrame的列名列表
                    columns = df.columns.tolist()
                    # 找到"整体耗时"这一列的索引
                    try:
                        # 尝试找到"整体耗时"这一列的索引
                        time_index = columns.index('整体耗时')
                    except ValueError:
                        try:
                            # 如果"整体耗时"列不存在，尝试找到"整体用时"这一列的索引
                            time_index = columns.index('整体用时')
                        except ValueError:
                            # 如果"整体用时"也不存在，可能需要处理错误或选择一个备选方案
                            time_index = len(columns)  # 假设所有列都需要保留

                    # 在遍历DataFrame的每一行之前，确定需要pop的列
                    columns_to_pop = columns[:time_index]
                    
                    for index, row in df.iterrows():
                        # 尝试将工作证编号先转换为整数，然后转换为字符串
                        try:
                            work_certificate_number = str(int(row.get('工作证编号')))
                        # 如果转换失败，则将工作证编号置为空字符串
                        except (ValueError, TypeError):
                            work_certificate_number = ''
                            
                        if pd.isna(work_certificate_number) or not re.match(r'^\d{5,}$', str(work_certificate_number)):
                            print(f"跳过文件 {file_name} 中的行 {index}: 工作证编号 '{work_certificate_number}' 不是大于四位数的数字")
                            continue
                        
                        # 如果乘务班组、姓名、工作证编号都为空，则跳过当前行不录入
                        if pd.isna(row.get('乘务班组')) and pd.isna(row.get('姓名')) and (pd.isna(row.get('工作证编号')) or not re.match(r'^\d{5,}$', work_certificate_number)):
                            print(f"跳过文件 {file_name} 中的行 {index}: 乘务班组、姓名、工作证编号都为空")
                            continue  
                        
                        # 对时间型列 日期、记录日期 进行处理
                        record_date_str = row.get('记录日期') or row.get('日期')
                        try:
                            # 将数据中的 20231110 转换为 2023-11-10
                            record_date = datetime.strptime(str(record_date_str), '%Y%m%d').date() if pd.notna(record_date_str) else None
                        except ValueError:
                            print(f"跳过文件 {file_name} 中的行 {index}: 记录日期 '{record_date_str}' 格式错误")
                            continue
                        crew_group = row.get('乘务班组')
                        if pd.notna(crew_group) and '高峰' in crew_group:
                            crew_group = '乘务高峰组'
                        # 考核结果的映射
                        assessment_result = self.map_assessment_result(row.get('考核结果'))

                        additional_data = row.to_dict()
                        additional_data = {k: (None if pd.isna(v) else v) for k, v in additional_data.items()}
                        for field in columns_to_pop:
                            additional_data.pop(field, None)

                        Assessment_Base.objects.create(
                            file_name=file_name,
                            record_date=record_date,
                            crew_group=crew_group,
                            name=row.get('姓名'),
                            work_certificate_number=work_certificate_number,
                            train_model=row.get('车型'),
                            assessment_item=row.get('考核项目'),
                            assessment_result=assessment_result,
                            additional_data=additional_data
                        )

            except Exception as e:
                return Response({'detail': f'处理文件 {file_name} 时发生错误: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': '所有文件上传成功。'}, status=status.HTTP_201_CREATED)

# 定义分页规则
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 1000

# 驾驶员基本信息筛选排序视图
class AssessmentBaseViewSet(viewsets.ModelViewSet):
    queryset = Assessment_Base.objects.all()
    serializer_class = AssessmentBaseSerializer
    pagination_class = StandardResultsSetPagination
    # 添加OrderingFilter到过滤后端
    # 参考文档 https://www.django-rest-framework.org/api-guide/filtering/#orderingfilter
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    # 允许排序的字段
    ordering_fields = '__all__'  # 允许所有字段可以排序
    ordering = ['record_date']  # 默认按照记录日期升序排列
    
    # 获取所有不重复的 train_model 和 assessment_item 组合，为前端的 科目 提供选项框
    @action(detail=False, methods=['get'], url_path='all-train-and-assessment')
    def all_train_and_assessment_items(self, request, *args, **kwargs):
        # 使用 Django 的 .values() 和 .distinct() 来获取所有不重复的 train_model 和 assessment_item 组合
        queryset = self.get_queryset().values('train_model', 'assessment_item').distinct()

        # 使用 set 来存储唯一的组合
        unique_combinations = set()

        # 遍历查询集，为每个组合创建一个唯一的字符串标识符，然后添加到 set 中
        for item in queryset:
            combination = f"{item['train_model']}-{item['assessment_item']}"
            unique_combinations.add(combination)

        # 将 set 转换回列表形式的数据，分别返回 train_model 和 assessment_item 字段
        result = []
        for combination in unique_combinations:
            train_model, assessment_item = combination.split('-', 1)
            result.append({"train_model": train_model, "assessment_item": assessment_item})

        return Response(result)
    
    # 重写 get_queryset 方法，以便根据日期范围筛选查询集
    def get_queryset(self):
        queryset = super().get_queryset()  # 获取默认查询集
        # 从前端传递的查询参数 params 中获取各参数进行筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        train_model_line = self.request.query_params.get('train_model_line', None)
        train_model = self.request.query_params.get('train_model', None)
        assessment_item = self.request.query_params.get('assessment_item', None)

        # 根据日期范围筛选查询集
        if start_date and end_date:
            queryset = queryset.filter(record_date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(record_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(record_date__lte=end_date)

        # 参考 https://github.com/encode/django-rest-framework/blob/master/rest_framework/filters.py
        query_conditions = []

        # 检查 train_model_line 是否有值
        if train_model_line:
            # 如果有值，添加一个条件来匹配以该值开始的 train_model
            query_conditions.append(Q(train_model__startswith=train_model_line))
        # 如果 train_model_line 为空，即前端的选项框中选取了 所有线路，不添加该条件，从而不限制查询结果

        # 构建一个精确匹配 train_model 的车型匹配
        if train_model:
            query_conditions.append(Q(train_model=train_model))

        # 构建一个精确匹配 assessment_item 的考核项目匹配
        if assessment_item:
            query_conditions.append(Q(assessment_item=assessment_item))

        # 对查询集 queryset 应用所有筛选条件
        if query_conditions:
            # 使用 reduce 和 operator.and_ 来将所有筛选条件连接起来
            # 参考 https://github.com/encode/django-rest-framework/blob/master/rest_framework/filters.py
            queryset = queryset.filter(reduce(operator.and_, query_conditions))

        return queryset

    @action(detail=False, methods=['get'], url_path='unpaged-data')
    def unpaged_data(self, request, *args, **kwargs):
        # 重用定义好的 get_queryset 方法来获取满足筛选条件的全量数据（不分页）
        queryset = self.get_queryset()
        
        # 使用serializer来序列化数据
        serializer = self.get_serializer(queryset, many=True)
        
        # 返回序列化后的数据
        return Response(serializer.data)

# 保存操作分类视图
class SaveClassification(APIView):
    
    def post(self, request, *args, **kwargs):
        '''
        前端发送的数据格式为：
        {
            "file_name": "10tsm1.csv",
            "classifications": {
                "解锁逃生门箱体解锁把手": "识故",
                "取下逃生门箱体上盖板": "排故",
                ...
            }
        }
        '''
        file_name = request.data.get('file_name')
        classifications = request.data.get('classifications')

        # 找到所有具有该 file_name 的 Assessment_Base 实例
        assessment_bases = Assessment_Base.objects.filter(file_name=file_name)
        if not assessment_bases.exists():
            return Response({"error": "File name not found."}, status=status.HTTP_404_NOT_FOUND)

        for assessment_base in assessment_bases:
            # 对于每个找到的Assessment_Base实例，更新或创建Assessment_Classification记录
            for key, category in classifications.items():
                # 确保这里的`assessment_base`和`data_key`足以唯一标识一个记录
                # ORM 数据库提供部分更新和首次创建的支持
                Assessment_Classification.objects.update_or_create(
                    assessment_base=assessment_base,
                    file_name=file_name,
                    data_key=key,
                    defaults={'category': category}
    )

        return Response({"status": "success"}, status=status.HTTP_200_OK)
    
class DataKeyCategoryList(APIView):
    '''
    从后端请求到的数据格式也为：
    {
        "file_name": "10tsm1.csv",
        "classifications": {
            "解锁逃生门箱体解锁把手": "识故",
            "取下逃生门箱体上盖板": "排故",
            ...
        }
    }
    '''
    def get(self, request, *args, **kwargs):
        # 首先获取所有唯一的 file_name
        file_names = Assessment_Classification.objects.values_list('file_name', flat=True).distinct()
        # 创建一个空列表，用于存储响应数据
        response_data = []

        # 遍历每个file_name，为其构建 classifications 字典
        for file_name in file_names:
            data_key_categories = Assessment_Classification.objects.filter(file_name=file_name).values('data_key', 'category')
            # 使用字典推导式构建 classifications 字典
            classifications = {item['data_key']: item['category'] for item in data_key_categories}
            
            # 将构建的数据添加到响应列表中
            response_data.append({
                "file_name": file_name,
                "classifications": classifications
            })

        return Response(response_data, status=status.HTTP_200_OK)