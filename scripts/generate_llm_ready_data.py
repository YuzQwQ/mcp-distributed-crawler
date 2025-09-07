#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成DFD处理过程命名规范的LLM就绪数据（第三阶段）
"""

import json
import os
from datetime import datetime
from pathlib import Path

def load_knowledge_base_files(base_filename):
    """加载知识库文件"""
    kb_dir = Path("shared_data/knowledge_base")
    
    # 定义文件类型
    file_types = ['concepts', 'rules', 'patterns', 'cases', 'nlp_mappings']
    
    data = {}
    metadata = None
    
    for file_type in file_types:
        file_path = kb_dir / f"{base_filename}_{file_type}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                data[f"dfd_{file_type}"] = content.get('data', [])
                if metadata is None:
                    metadata = content.get('metadata', {})
    
    return data, metadata

def generate_llm_ready_json(data, metadata, base_filename):
    """生成LLM就绪的JSON数据"""
    
    # 计算统计信息
    statistics = {}
    for key, value in data.items():
        if key.startswith('dfd_'):
            stat_key = key.replace('dfd_', '') + '_count'
            statistics[stat_key] = len(value) if isinstance(value, list) else 0
    
    # 构建LLM就绪数据结构
    llm_ready_data = {
        "metadata": metadata,
        "statistics": statistics
    }
    
    # 添加所有数据类别
    llm_ready_data.update(data)
    
    return llm_ready_data

def save_llm_ready_data(data, base_filename):
    """保存LLM就绪数据"""
    # 创建输出目录
    output_dir = Path("shared_data/json_llm_ready")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    filename = f"{base_filename}_{timestamp}.json"
    file_path = output_dir / filename
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(file_path)

def main():
    try:
        base_filename = "DFD_处理过程命名规范"
        
        print(f"🔄 开始生成 {base_filename} 的LLM就绪数据...")
        
        # 加载知识库文件
        data, metadata = load_knowledge_base_files(base_filename)
        
        if not data:
            print("❌ 未找到知识库文件")
            return
        
        print(f"✅ 成功加载知识库数据")
        print(f"📋 数据类别: {list(data.keys())}")
        
        # 生成LLM就绪数据
        llm_ready_data = generate_llm_ready_json(data, metadata, base_filename)
        
        print(f"✅ 成功生成LLM就绪数据结构")
        
        # 保存LLM就绪数据
        saved_path = save_llm_ready_data(llm_ready_data, base_filename)
        
        print(f"✅ LLM就绪数据已保存到: {saved_path}")
        
        # 显示统计信息
        print("\n📊 数据统计:")
        for key, value in llm_ready_data['statistics'].items():
            category_name = key.replace('_count', '')
            print(f"  - {category_name}: {value} 个")
        
        print("\n🎉 第三阶段LLM就绪数据生成完成！")
        
    except Exception as e:
        print(f"❌ 生成过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()