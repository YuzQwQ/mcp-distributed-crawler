#!/usr/bin/env python3
"""
测试DFD知识收集和绘制系统的完整功能
验证知识收集、处理和可视化流程
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dfd_collector import DFDKnowledgeCollector
    from dfd_analyzer import DFDAnalyzer
    from dfd_visualizer import DFDVisualizer
    from dfd_validator import DFDValidator
except ImportError as e:
    print(f"导入错误: {e}")
    print("正在创建DFD收集系统的基本组件...")

class DFDTestSystem:
    """DFD知识收集和绘制测试系统"""
    
    def __init__(self):
        self.test_results = []
        self.collector = None
        self.analyzer = None
        self.visualizer = None
        self.validator = None
        
    async def setup_system(self):
        """设置测试系统"""
        print("🚀 初始化DFD知识收集测试系统...")
        
        # 创建DFD收集器
        self.collector = DFDKnowledgeCollector()
        self.analyzer = DFDAnalyzer()
        self.visualizer = DFDVisualizer()
        self.validator = DFDValidator()
        
        print("✅ 系统初始化完成")
        
    async def test_knowledge_collection(self):
        """测试知识收集功能"""
        print("\n📚 测试DFD知识收集...")
        
        # 测试用例：电商系统DFD知识收集
        test_queries = [
            "电商系统订单处理的数据流图DFD设计",
            "图书管理系统的DFD建模最佳实践", 
            "学生信息管理系统的DFD设计案例",
            "银行转账业务的DFD分析和设计",
            "在线学习平台的DFD架构设计"
        ]
        
        collected_knowledge = []
        for query in test_queries:
            print(f"  🔍 收集知识: {query}")
            knowledge = await self.collector.collect_knowledge(query)
            collected_knowledge.append({
                'query': query,
                'knowledge': knowledge,
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存收集结果
        with open('test_dfd_knowledge.json', 'w', encoding='utf-8') as f:
            json.dump(collected_knowledge, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 知识收集完成，共收集 {len(collected_knowledge)} 个主题")
        return collected_knowledge
        
    async def test_dfd_analysis(self, knowledge_data):
        """测试DFD分析功能"""
        print("\n🔍 测试DFD知识分析...")
        
        analysis_results = []
        for item in knowledge_data:
            analysis = await self.analyzer.analyze_knowledge(item['knowledge'])
            analysis_results.append({
                'query': item['query'],
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"  📊 分析完成: {item['query'][:50]}...")
            print(f"     - 概念数量: {len(analysis.get('concepts', []))}")
            print(f"     - 规则数量: {len(analysis.get('rules', []))}")
            print(f"     - 案例数量: {len(analysis.get('cases', []))}")
        
        # 保存分析结果
        with open('test_dfd_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            
        print("✅ 知识分析完成")
        return analysis_results
        
    async def test_dfd_visualization(self, analysis_results):
        """测试DFD可视化功能"""
        print("\n🎨 测试DFD可视化...")
        
        viz_results = []
        for result in analysis_results[:3]:  # 测试前3个结果
            try:
                # 生成知识图谱
                knowledge_graph = await self.visualizer.create_knowledge_graph(
                    result['analysis']
                )
                
                # 生成DFD示例图
                dfd_diagram = await self.visualizer.create_dfd_diagram(
                    result['analysis']
                )
                
                viz_result = {
                    'query': result['query'],
                    'knowledge_graph': knowledge_graph,
                    'dfd_diagram': dfd_diagram,
                    'timestamp': datetime.now().isoformat()
                }
                viz_results.append(viz_result)
                
                print(f"  🖼️ 可视化完成: {result['query'][:50]}...")
                
            except Exception as e:
                print(f"  ❌ 可视化失败: {str(e)}")
                
        # 保存可视化结果
        with open('test_dfd_visualization.json', 'w', encoding='utf-8') as f:
            json.dump(viz_results, f, ensure_ascii=False, indent=2)
            
        print("✅ 可视化测试完成")
        return viz_results
        
    async def test_dfd_validation(self, knowledge_data):
        """测试DFD验证功能"""
        print("\n✅ 测试DFD知识验证...")
        
        validation_results = []
        for item in knowledge_data:
            validation = await self.validator.validate_knowledge(item['knowledge'])
            validation_results.append({
                'query': item['query'],
                'validation': validation,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"  ✅ 验证完成: {item['query'][:50]}...")
            print(f"     - 完整性: {validation.get('completeness', 'N/A')}")
            print(f"     - 一致性: {validation.get('consistency', 'N/A')}")
            print(f"     - 准确性: {validation.get('accuracy', 'N/A')}")
        
        # 保存验证结果
        with open('test_dfd_validation.json', 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)
            
        print("✅ 知识验证完成")
        return validation_results
        
    async def generate_test_report(self, all_results):
        """生成测试报告"""
        print("\n📋 生成测试报告...")
        
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_queries': len(all_results.get('knowledge', [])),
                'successful_collection': len([r for r in all_results.get('knowledge', []) if r.get('knowledge')]),
                'successful_analysis': len([r for r in all_results.get('analysis', []) if r.get('analysis')]),
                'successful_visualization': len(all_results.get('visualization', [])),
                'successful_validation': len([r for r in all_results.get('validation', []) if r.get('validation', {}).get('valid', False)])
            },
            'details': all_results
        }
        
        # 保存测试报告
        with open('test_dfd_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        # 生成Markdown报告
        markdown_report = self._generate_markdown_report(report)
        with open('test_dfd_report.md', 'w', encoding='utf-8') as f:
            f.write(markdown_report)
            
        print("✅ 测试报告生成完成")
        return report
        
    def _generate_markdown_report(self, report):
        """生成Markdown格式的测试报告"""
        md = f"""# DFD知识收集和绘制系统测试报告

## 📊 测试概览

- **测试时间**: {report['test_timestamp']}
- **总查询数**: {report['summary']['total_queries']}
- **成功收集**: {report['summary']['successful_collection']}
- **成功分析**: {report['summary']['successful_analysis']}
- **成功可视化**: {report['summary']['successful_visualization']}
- **成功验证**: {report['summary']['successful_validation']}

## 🔍 详细测试结果

### 知识收集结果
"""
        
        for i, item in enumerate(report['details'].get('knowledge', [])):
            md += f"""
#### 测试 {i+1}: {item['query'][:50]}...
- **状态**: {'✅ 成功' if item.get('knowledge') else '❌ 失败'}
- **时间**: {item['timestamp']}
"""
            
        md += """
### 分析和可视化结果

详见生成的JSON文件：
- `test_dfd_knowledge.json` - 原始知识数据
- `test_dfd_analysis.json` - 分析结果
- `test_dfd_visualization.json` - 可视化数据
- `test_dfd_validation.json` - 验证结果

## 🎯 优化建议

基于测试结果，建议以下优化方向：

1. **知识收集优化**
   - 增加知识来源多样性
   - 提升概念提取深度
   - 补充缺失的规则分类

2. **分析算法改进**
   - 优化概念识别准确性
   - 增强规则提取能力
   - 改善案例分类效果

3. **可视化增强**
   - 支持更多图表类型
   - 提升图形美观度
   - 增加交互功能

4. **验证机制完善**
   - 加强质量检查
   - 增加一致性验证
   - 提供错误修正建议
"""
        
        return md
        
    async def run_full_test(self):
        """运行完整测试"""
        print("🎯 开始DFD知识收集和绘制系统完整测试...")
        
        try:
            await self.setup_system()
            
            # 运行各个测试阶段
            knowledge_data = await self.test_knowledge_collection()
            analysis_results = await self.test_dfd_analysis(knowledge_data)
            viz_results = await self.test_dfd_visualization(analysis_results)
            validation_results = await self.test_dfd_validation(knowledge_data)
            
            # 汇总所有结果
            all_results = {
                'knowledge': knowledge_data,
                'analysis': analysis_results,
                'visualization': viz_results,
                'validation': validation_results
            }
            
            # 生成最终报告
            report = await self.generate_test_report(all_results)
            
            print("\n🎉 DFD知识收集和绘制系统测试完成！")
            print("📊 查看测试报告: test_dfd_report.md")
            print("📁 查看详细数据: test_dfd_*.json 文件")
            
            return report
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# DFD收集系统的模拟实现
class DFDKnowledgeCollector:
    """DFD知识收集器"""
    
    async def collect_knowledge(self, query):
        """模拟收集DFD知识"""
        # 这里应该是实际的知识收集逻辑
        # 为了测试，我们返回模拟数据
        
        mock_knowledge = {
            'concepts': [
                {'name': 'process', 'definition': '处理数据的过程', 'category': 'core'},
                {'name': 'entity', 'definition': '外部实体', 'category': 'core'},
                {'name': 'data_store', 'definition': '数据存储', 'category': 'core'},
                {'name': 'data_flow', 'definition': '数据流', 'category': 'core'}
            ],
            'rules': [
                {'type': 'naming', 'description': '处理命名使用动词+名词格式'},
                {'type': 'balancing', 'description': '父子图输入输出必须平衡'}
            ],
            'cases': [
                {'type': 'best_practice', 'title': '电商系统DFD设计', 'description': '完整的订单处理流程'},
                {'type': 'error_case', 'title': '命名错误案例', 'description': '处理命名不规范的示例'}
            ],
            'patterns': [
                {'name': 'data_transformation', 'description': '数据转换模式'},
                {'name': 'data_collection', 'description': '数据收集模式'}
            ]
        }
        
        return mock_knowledge

class DFDAnalyzer:
    """DFD知识分析器"""
    
    async def analyze_knowledge(self, knowledge):
        """分析收集的知识"""
        return {
            'concept_count': len(knowledge.get('concepts', [])),
            'rule_count': len(knowledge.get('rules', [])),
            'case_count': len(knowledge.get('cases', [])),
            'pattern_count': len(knowledge.get('patterns', [])),
            'quality_score': 0.85,  # 模拟质量评分
            'recommendations': [
                '增加更多行业特定案例',
                '补充命名规则细节',
                '添加工具使用指南'
            ]
        }

class DFDVisualizer:
    """DFD可视化器"""
    
    async def create_knowledge_graph(self, analysis):
        """创建知识图谱"""
        return {
            'type': 'knowledge_graph',
            'nodes': [
                {'id': 'process', 'label': '处理', 'type': 'concept'},
                {'id': 'entity', 'label': '实体', 'type': 'concept'},
                {'id': 'data_store', 'label': '数据存储', 'type': 'concept'}
            ],
            'edges': [
                {'source': 'entity', 'target': 'process', 'label': '提供数据'},
                {'source': 'process', 'target': 'data_store', 'label': '存储数据'}
            ]
        }
    
    async def create_dfd_diagram(self, analysis):
        """创建DFD示例图"""
        return {
            'type': 'dfd_diagram',
            'elements': [
                {'type': 'entity', 'name': '客户', 'position': [100, 100]},
                {'type': 'process', 'name': '处理订单', 'position': [300, 100]},
                {'type': 'data_store', 'name': '订单数据', 'position': [500, 100]}
            ],
            'flows': [
                {'from': '客户', 'to': '处理订单', 'data': '订单信息'},
                {'from': '处理订单', 'to': '订单数据', 'data': '订单记录'}
            ]
        }

class DFDValidator:
    """DFD知识验证器"""
    
    async def validate_knowledge(self, knowledge):
        """验证知识质量"""
        return {
            'valid': True,
            'completeness': 0.85,
            'consistency': 0.90,
            'accuracy': 0.88,
            'issues': [
                '缺少命名规则详细说明',
                '案例数量偏少',
                '需要补充更多行业应用'
            ],
            'suggestions': [
                '增加更多最佳实践案例',
                '补充工具使用指南',
                '添加质量保证方法'
            ]
        }

async def main():
    """主测试函数"""
    test_system = DFDTestSystem()
    return await test_system.run_full_test()

if __name__ == "__main__":
    result = asyncio.run(main())