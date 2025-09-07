#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DFD知识库分析工具

快速分析当前DFD知识库的内容和质量状况
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter

def analyze_dfd_knowledge_base():
    """分析DFD知识库"""
    knowledge_base_dir = Path("shared_data/knowledge_base")
    
    if not knowledge_base_dir.exists():
        print(f"错误：知识库目录不存在 - {knowledge_base_dir}")
        return
    
    print("DFD知识库分析报告")
    print("=" * 50)
    
    # 统计文件数量
    dfd_files = list(knowledge_base_dir.glob("*DFD*.json"))
    summary_files = [f for f in dfd_files if f.name.endswith('_summary.json')]
    content_files = [f for f in dfd_files if not f.name.endswith('_summary.json')]
    
    print(f"\n📊 文件统计：")
    print(f"  总DFD相关文件：{len(dfd_files)}")
    print(f"  内容文件：{len(content_files)}")
    print(f"  汇总文件：{len(summary_files)}")
    
    # 分析文件类型分布
    file_types = defaultdict(int)
    for file in content_files:
        if '_concepts.json' in file.name:
            file_types['concepts'] += 1
        elif '_rules.json' in file.name:
            file_types['rules'] += 1
        elif '_cases.json' in file.name:
            file_types['cases'] += 1
        elif '_patterns.json' in file.name:
            file_types['patterns'] += 1
        elif '_nlp_mappings.json' in file.name:
            file_types['nlp_mappings'] += 1
    
    print(f"\n📋 知识类型分布：")
    for file_type, count in file_types.items():
        print(f"  {file_type}: {count} 个文件")
    
    # 分析知识来源
    sources = set()
    total_concepts = 0
    total_rules = 0
    total_cases = 0
    
    concept_types = Counter()
    rule_categories = Counter()
    case_types = Counter()
    
    print(f"\n🔍 内容分析：")
    
    # 分析概念文件
    concept_files = [f for f in content_files if '_concepts.json' in f.name]
    for file in concept_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 提取来源信息
            metadata = data.get('metadata', {})
            source_title = metadata.get('source_title', '未知来源')
            sources.add(source_title)
            
            # 统计概念
            concepts = data.get('data', [])
            total_concepts += len(concepts)
            
            for concept in concepts:
                concept_type = concept.get('type', '未分类')
                concept_types[concept_type] += 1
                
        except Exception as e:
            print(f"  ⚠️ 读取文件失败 {file.name}: {e}")
    
    # 分析规则文件
    rule_files = [f for f in content_files if '_rules.json' in f.name]
    for file in rule_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            rules = data.get('data', [])
            total_rules += len(rules)
            
            for rule in rules:
                category = rule.get('category', '未分类')
                rule_categories[category] += 1
                
        except Exception as e:
            print(f"  ⚠️ 读取规则文件失败 {file.name}: {e}")
    
    # 分析案例文件
    case_files = [f for f in content_files if '_cases.json' in f.name]
    for file in case_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            cases = data.get('data', [])
            total_cases += len(cases)
            
            for case in cases:
                case_type = case.get('type', '未分类')
                case_types[case_type] += 1
                
        except Exception as e:
            print(f"  ⚠️ 读取案例文件失败 {file.name}: {e}")
    
    print(f"  总概念数：{total_concepts}")
    print(f"  总规则数：{total_rules}")
    print(f"  总案例数：{total_cases}")
    
    print(f"\n📚 知识来源 ({len(sources)} 个)：")
    for i, source in enumerate(sorted(sources), 1):
        print(f"  {i}. {source}")
    
    print(f"\n🏷️ 概念类型分布：")
    for concept_type, count in concept_types.most_common():
        print(f"  {concept_type}: {count}")
    
    print(f"\n📏 规则类别分布：")
    for category, count in rule_categories.most_common():
        print(f"  {category}: {count}")
    
    print(f"\n📝 案例类型分布：")
    for case_type, count in case_types.most_common():
        print(f"  {case_type}: {count}")
    
    # 质量评估
    print(f"\n⭐ 质量评估：")
    
    # 检查核心概念覆盖度
    required_concepts = {'process', 'entity', 'data_store', 'data_flow'}
    found_concepts = set(concept_types.keys())
    concept_coverage = len(found_concepts & required_concepts) / len(required_concepts) * 100
    
    print(f"  核心概念覆盖度：{concept_coverage:.1f}%")
    missing_concepts = required_concepts - found_concepts
    if missing_concepts:
        print(f"  缺失核心概念：{', '.join(missing_concepts)}")
    
    # 检查规则分类覆盖度
    expected_rule_categories = {'hierarchy', 'connection', 'naming'}
    found_categories = set(rule_categories.keys())
    rule_coverage = len(found_categories & expected_rule_categories) / len(expected_rule_categories) * 100
    
    print(f"  规则分类覆盖度：{rule_coverage:.1f}%")
    missing_categories = expected_rule_categories - found_categories
    if missing_categories:
        print(f"  缺失规则分类：{', '.join(missing_categories)}")
    
    # 数据质量指标
    avg_concepts_per_source = total_concepts / len(sources) if sources else 0
    avg_rules_per_source = total_rules / len(rule_files) if rule_files else 0
    
    print(f"  平均每来源概念数：{avg_concepts_per_source:.1f}")
    print(f"  平均每文件规则数：{avg_rules_per_source:.1f}")
    
    # 生成改进建议
    print(f"\n💡 改进建议：")
    
    if concept_coverage < 100:
        print(f"  1. 补充缺失的核心概念：{', '.join(missing_concepts)}")
    
    if rule_coverage < 100:
        print(f"  2. 完善规则分类：{', '.join(missing_categories)}")
    
    if total_cases < 10:
        print(f"  3. 增加更多实践案例（当前仅{total_cases}个）")
    
    if len(sources) < 5:
        print(f"  4. 扩展知识来源（当前仅{len(sources)}个来源）")
    
    if avg_concepts_per_source < 5:
        print(f"  5. 深化每个来源的概念提取")
    
    print(f"\n📋 推荐使用的提示词类型：")
    
    if concept_coverage < 80:
        print(f"  • 概念库扩展提示词 - 补充核心概念")
    
    if rule_coverage < 80:
        print(f"  • 规则库完善提示词 - 完善规则体系")
    
    if total_cases < 20:
        print(f"  • 案例库丰富提示词 - 增加实践案例")
    
    if len(sources) < 10:
        print(f"  • 领域特定知识扩展提示词 - 扩展应用领域")
    
    print(f"\n📖 详细提示词请查看：dfd_knowledge_enhancement_prompts.md")
    
    return {
        'total_files': len(content_files),
        'total_concepts': total_concepts,
        'total_rules': total_rules,
        'total_cases': total_cases,
        'sources_count': len(sources),
        'concept_coverage': concept_coverage,
        'rule_coverage': rule_coverage
    }

if __name__ == "__main__":
    analyze_dfd_knowledge_base()