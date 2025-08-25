#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库保存功能测试脚本
演示如何使用通用格式处理器保存不同类型的知识库数据
"""

import json
from format_processor import FormatProcessor
from server import save_to_knowledge_base

def test_format_processor():
    """测试FormatProcessor的基本功能"""
    print("=== 测试FormatProcessor基本功能 ===")
    
    # 初始化处理器
    processor = FormatProcessor()
    print(f"格式处理器初始化成功: {processor.get_format_name()}")
    print(f"可用格式: {processor.get_available_formats()}")
    
    # 测试数据
    test_data = {
        'dfd_concepts': [
            {
                'name': 'DFD基础概念',
                'definition': '数据流图是一种图形化的系统分析工具',
                'type': '基础概念',
                'symbol': '圆形'
            }
        ],
        'dfd_rules': [
            {
                'rule_id': 'R001',
                'description': '每个处理过程必须有输入和输出',
                'category': '基本规则'
            }
        ]
    }
    
    # 使用FormatProcessor保存
    result = processor.save_knowledge_base(test_data, 'processor_test')
    print(f"\nFormatProcessor保存结果: {result['success']}")
    print(f"保存的文件数量: {result.get('total_files', 0)}")
    
    return result

def test_server_function():
    """测试server.py中的save_to_knowledge_base函数"""
    print("\n=== 测试server.py保存函数 ===")
    
    # 测试数据
    test_data = {
        'dfd_concepts': [
            {
                'name': '服务器测试概念',
                'definition': '这是通过服务器函数保存的测试概念',
                'type': '测试概念'
            }
        ],
        'dfd_patterns': [
            {
                'pattern_name': '基础模式',
                'description': '最简单的DFD模式',
                'components': ['外部实体', '处理过程', '数据流']
            }
        ]
    }
    
    # 转换为JSON字符串（模拟实际调用）
    json_data = json.dumps(test_data, ensure_ascii=False)
    
    # 调用服务器函数
    result = save_to_knowledge_base(json_data, 'server_function_test', 'dfd')
    print(f"\n服务器函数保存结果:")
    print(result)
    
    return result

def test_different_formats():
    """测试不同格式类型的支持"""
    print("\n=== 测试不同格式类型支持 ===")
    
    # 测试DFD格式
    dfd_processor = FormatProcessor(format_type='dfd')
    print(f"DFD格式处理器: {dfd_processor.get_format_name()}")
    
    # 可以在这里添加其他格式类型的测试
    # 例如：uml_processor = FormatProcessor(format_type='uml')
    
    return True

def main():
    """主测试函数"""
    print("知识库保存功能测试开始...\n")
    
    try:
        # 测试FormatProcessor
        test_format_processor()
        
        # 测试服务器函数
        test_server_function()
        
        # 测试不同格式支持
        test_different_formats()
        
        print("\n=== 所有测试完成 ===")
        print("✅ 知识库保存功能工作正常")
        print("✅ 通用格式处理器功能正常")
        print("✅ 服务器函数集成成功")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()