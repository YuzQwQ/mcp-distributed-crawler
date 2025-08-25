#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动处理DFD处理过程命名规范数据到知识库
"""

import json
import sys
sys.path.append('.')
from server import save_to_knowledge_base
from format_processor import FormatProcessor

def main():
    try:
        # 读取DFD处理过程命名规范的搜索结果
        with open('data/parsed/DFD_处理过程命名规范_动词_名词_20250814_091637/google_DFD_处理过程命名规范_动词_名词_20250814_091637.json', 'r', encoding='utf-8') as f:
            search_data = json.load(f)
        
        print("✅ 成功读取搜索数据")
        print(f"📊 搜索结果数量: {len(search_data['results'])}")
        
        # 提取搜索结果的摘要内容
        content_analysis = '\n'.join([f"{result['title']}: {result['snippet']}" for result in search_data['results']])
        
        print("✅ 成功提取内容摘要")
        
        # 创建格式处理器
        processor = FormatProcessor()
        print(f"✅ 格式处理器初始化: {processor.get_format_name()}")
        
        # 提取知识库数据
        extracted_data = processor.extract_knowledge(
            content_analysis, 
            'https://google.com/search?q=DFD+处理过程命名规范+动词+名词',
            'DFD处理过程命名规范'
        )
        
        print("✅ 成功提取知识库数据")
        print(f"📋 提取的数据类别: {list(extracted_data.keys())}")
        
        # 生成JSON结构
        json_obj = processor.generate_json_structure(
            extracted_data, 
            'https://google.com/search?q=DFD+处理过程命名规范+动词+名词',
            'DFD处理过程命名规范'
        )
        
        print("✅ 成功生成JSON结构")
        
        # 调用知识库保存函数
        result = save_to_knowledge_base(json.dumps(json_obj), 'DFD_处理过程命名规范')
        print("\n📁 知识库保存结果:")
        print(result)
        
    except Exception as e:
        print(f"❌ 处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()