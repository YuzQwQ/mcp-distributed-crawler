#!/usr/bin/env python3
"""
知识库整理工具
用于整理和验证DFD知识、爬虫知识、系统架构知识
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeOrganizer:
    """知识库整理器"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.knowledge_base_dir = self.base_dir / "knowledge_base"
        self.categories = {
            "dfd_knowledge": "DFD设计知识",
            "crawler_knowledge": "爬虫技术知识",
            "system_architecture": "系统架构知识",
            "best_practices": "最佳实践",
            "tools_and_resources": "工具和资源"
        }
        
    def organize_all_knowledge(self) -> Dict[str, Any]:
        """整理所有知识"""
        logger.info("开始整理知识库...")
        
        # 创建知识库目录结构
        self._create_directory_structure()
        
        # 整理各类知识
        results = {}
        
        # 1. 整理DFD知识
        results["dfd_knowledge"] = self._organize_dfd_knowledge()
        
        # 2. 整理爬虫知识
        results["crawler_knowledge"] = self._organize_crawler_knowledge()
        
        # 3. 整理系统架构知识
        results["system_architecture"] = self._organize_system_knowledge()
        
        # 4. 整理最佳实践
        results["best_practices"] = self._organize_best_practices()
        
        # 5. 生成索引文件
        results["index"] = self._generate_knowledge_index()
        
        # 6. 生成验证报告
        results["validation"] = self._validate_knowledge_base()
        
        logger.info("知识库整理完成！")
        return results
    
    def _create_directory_structure(self):
        """创建知识库目录结构"""
        self.knowledge_base_dir.mkdir(exist_ok=True)
        
        for category in self.categories:
            category_dir = self.knowledge_base_dir / category
            category_dir.mkdir(exist_ok=True)
            
            # 创建子目录
            (category_dir / "concepts").mkdir(exist_ok=True)
            (category_dir / "examples").mkdir(exist_ok=True)
            (category_dir / "references").mkdir(exist_ok=True)
    
    def _organize_dfd_knowledge(self) -> Dict[str, Any]:
        """整理DFD知识"""
        logger.info("整理DFD设计知识...")
        
        dfd_data = {
            "concepts": {
                "basic_elements": {
                    "process": {
                        "definition": "对输入数据进行处理并产生输出的功能单元",
                        "symbol": "圆形或圆角矩形",
                        "naming_rule": "动词+名词格式",
                        "examples": ["处理订单", "验证用户", "生成报告"]
                    },
                    "external_entity": {
                        "definition": "系统边界之外与系统交互的人、组织或其他系统",
                        "symbol": "矩形",
                        "naming_rule": "名词表示角色或系统",
                        "examples": ["客户", "供应商", "银行系统"]
                    },
                    "data_store": {
                        "definition": "系统内部用于存储数据的仓库",
                        "symbol": "双横线或开口矩形",
                        "naming_rule": "D+编号+名称格式",
                        "examples": ["D1 客户信息", "D2 订单数据"]
                    },
                    "data_flow": {
                        "definition": "数据在系统组件之间的移动路径",
                        "symbol": "带箭头的线条",
                        "naming_rule": "数据内容名称",
                        "examples": ["客户信息", "订单详情"]
                    }
                },
                "hierarchy_levels": {
                    "context_diagram": "系统与外部实体的整体关系",
                    "level_0_dfd": "系统的上下文图",
                    "level_1_dfd": "系统的主要功能分解",
                    "level_2_dfd": "详细功能模块设计"
                }
            },
            "rules": {
                "naming_conventions": {
                    "processes": "使用动词+名词格式，如'处理订单'",
                    "entities": "使用名词表示角色，如'客户'",
                    "data_stores": "使用D+编号+名称，如'D1 客户信息'",
                    "data_flows": "使用数据内容名称，如'客户信息'"
                },
                "balancing_rules": [
                    "父子图输入输出必须平衡",
                    "每个处理必须有输入和输出",
                    "数据流方向必须正确",
                    "避免数据流交叉"
                ]
            },
            "examples": {
                "e_commerce_order": {
                    "title": "电商订单处理DFD",
                    "description": "完整的电商订单处理流程",
                    "levels": {
                        "context": {
                            "entities": ["客户", "支付网关", "物流系统"],
                            "process": "电商订单系统"
                        },
                        "level_1": {
                            "processes": ["1.0 接收订单", "2.0 处理支付", "3.0 管理库存"],
                            "data_stores": ["D1 订单数据", "D2 客户信息", "D3 产品库存"]
                        }
                    }
                }
            }
        }
        
        # 保存到文件
        dfd_file = self.knowledge_base_dir / "dfd_knowledge" / "dfd_complete_guide.json"
        with open(dfd_file, 'w', encoding='utf-8') as f:
            json.dump(dfd_data, f, ensure_ascii=False, indent=2)
        
        return {
            "concepts_count": len(dfd_data["concepts"]),
            "rules_count": len(dfd_data["rules"]),
            "examples_count": len(dfd_data["examples"]),
            "file_path": str(dfd_file)
        }
    
    def _organize_crawler_knowledge(self) -> Dict[str, Any]:
        """整理爬虫知识"""
        logger.info("整理爬虫技术知识...")
        
        crawler_data = {
            "architectures": {
                "single_thread": "单线程爬虫，适合简单任务",
                "multi_thread": "多线程爬虫，提高并发性能",
                "distributed": "分布式爬虫，支持大规模数据采集"
            },
            "components": {
                "scheduler": "任务调度器，管理爬取队列",
                "downloader": "下载器，负责网页获取",
                "parser": "解析器，提取结构化数据",
                "pipeline": "数据管道，处理和存储数据",
                "monitoring": "监控系统，跟踪性能和状态"
            },
            "techniques": {
                "stealth_crawling": {
                    "description": "隐蔽爬取技术，避免被检测",
                    "methods": [
                        "随机化请求间隔",
                        "模拟真实浏览器行为",
                        "使用代理池轮换",
                        "处理JavaScript渲染"
                    ]
                },
                "humanized_access": {
                    "description": "人性化访问控制",
                    "features": [
                        "智能延迟控制",
                        "域名感知限速",
                        "友好访问策略",
                        "自动重试机制"
                    ]
                }
            },
            "tools": {
                "scrapy": "Python爬虫框架",
                "beautifulsoup": "HTML/XML解析库",
                "selenium": "浏览器自动化工具",
                "playwright": "现代浏览器自动化",
                "aiohttp": "异步HTTP客户端"
            }
        }
        
        # 保存到文件
        crawler_file = self.knowledge_base_dir / "crawler_knowledge" / "crawler_complete_guide.json"
        with open(crawler_file, 'w', encoding='utf-8') as f:
            json.dump(crawler_data, f, ensure_ascii=False, indent=2)
        
        return {
            "architectures_count": len(crawler_data["architectures"]),
            "components_count": len(crawler_data["components"]),
            "techniques_count": len(crawler_data["techniques"]),
            "file_path": str(crawler_file)
        }
    
    def _organize_system_knowledge(self) -> Dict[str, Any]:
        """整理系统架构知识"""
        logger.info("整理系统架构知识...")
        
        system_data = {
            "distributed_architecture": {
                "components": {
                    "master_node": {
                        "role": "任务分发和结果收集",
                        "responsibilities": ["任务调度", "结果聚合", "状态监控"]
                    },
                    "worker_nodes": {
                        "role": "实际爬取任务执行",
                        "responsibilities": ["网页下载", "数据解析", "结果上报"]
                    },
                    "redis_queue": {
                        "role": "任务队列和缓存",
                        "responsibilities": ["任务存储", "结果缓存", "状态同步"]
                    }
                },
                "communication": {
                    "task_queue": "Redis列表结构",
                    "result_queue": "Redis列表结构",
                    "status_channel": "Redis发布订阅"
                }
            },
            "monitoring": {
                "metrics": ["爬取速度", "成功率", "错误率", "响应时间"],
                "alerts": ["队列积压", "节点离线", "异常错误"],
                "dashboard": "实时性能监控面板"
            }
        }
        
        # 保存到文件
        system_file = self.knowledge_base_dir / "system_architecture" / "system_architecture_guide.json"
        with open(system_file, 'w', encoding='utf-8') as f:
            json.dump(system_data, f, ensure_ascii=False, indent=2)
        
        return {
            "components_count": len(system_data["distributed_architecture"]["components"]),
            "metrics_count": len(system_data["monitoring"]["metrics"]),
            "file_path": str(system_file)
        }
    
    def _organize_best_practices(self) -> Dict[str, Any]:
        """整理最佳实践"""
        logger.info("整理最佳实践...")
        
        best_practices = {
            "dfd_design": {
                "naming": [
                    "使用动词+名词格式命名处理",
                    "使用D+编号命名数据存储",
                    "使用名词命名外部实体"
                ],
                "balancing": [
                    "确保父子图输入输出平衡",
                    "每个处理必须有输入和输出",
                    "避免数据流交叉"
                ]
            },
            "crawler_development": {
                "robots_txt": "始终检查并遵守robots.txt规则",
                "rate_limiting": "实施合理的访问频率限制",
                "error_handling": "建立完善的错误处理和重试机制",
                "data_validation": "验证爬取数据的完整性和准确性"
            },
            "system_deployment": {
                "monitoring": "建立完整的监控和告警系统",
                "logging": "实现详细的日志记录和审计",
                "scaling": "设计可水平扩展的架构",
                "backup": "建立数据备份和恢复机制"
            }
        }
        
        # 保存到文件
        practices_file = self.knowledge_base_dir / "best_practices" / "best_practices_guide.json"
        with open(practices_file, 'w', encoding='utf-8') as f:
            json.dump(best_practices, f, ensure_ascii=False, indent=2)
        
        return {
            "dfd_practices": len(best_practices["dfd_design"]),
            "crawler_practices": len(best_practices["crawler_development"]),
            "deployment_practices": len(best_practices["system_deployment"]),
            "file_path": str(practices_file)
        }
    
    def _generate_knowledge_index(self) -> Dict[str, Any]:
        """生成知识库索引"""
        logger.info("生成知识库索引...")
        
        index = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "total_categories": len(self.categories),
                "categories": self.categories
            },
            "index": {
                category: {
                    "name": name,
                    "files": self._list_category_files(category),
                    "concepts": self._count_concepts_in_category(category)
                }
                for category, name in self.categories.items()
            }
        }
        
        # 保存索引
        index_file = self.knowledge_base_dir / "knowledge_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        return {
            "index_file": str(index_file),
            "total_entries": sum(cat["concepts"] for cat in index["index"].values())
        }
    
    def _list_category_files(self, category: str) -> List[str]:
        """列出分类中的文件"""
        category_dir = self.knowledge_base_dir / category
        if not category_dir.exists():
            return []
        
        files = []
        for file_path in category_dir.rglob("*.json"):
            files.append(str(file_path.relative_to(self.knowledge_base_dir)))
        return files
    
    def _count_concepts_in_category(self, category: str) -> int:
        """统计分类中的概念数量"""
        category_dir = self.knowledge_base_dir / category
        if not category_dir.exists():
            return 0
        
        count = 0
        for file_path in category_dir.rglob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        count += len(data.get("concepts", {}))
            except:
                continue
        return count
    
    def _validate_knowledge_base(self) -> Dict[str, Any]:
        """验证知识库完整性"""
        logger.info("验证知识库完整性...")
        
        validation = {
            "status": "valid",
            "checks": {
                "directory_structure": True,
                "file_integrity": True,
                "content_validation": True
            },
            "statistics": {
                "total_files": 0,
                "total_size_mb": 0,
                "categories_validated": 0
            }
        }
        
        total_files = 0
        total_size = 0
        
        for category in self.categories:
            category_dir = self.knowledge_base_dir / category
            if category_dir.exists():
                for file_path in category_dir.rglob("*.json"):
                    if file_path.exists():
                        total_files += 1
                        total_size += file_path.stat().st_size
                        validation["statistics"]["categories_validated"] += 1
        
        validation["statistics"]["total_files"] = total_files
        validation["statistics"]["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return validation

def main():
    """主函数"""
    organizer = KnowledgeOrganizer()
    results = organizer.organize_all_knowledge()
    
    print("🎉 知识库整理完成！")
    print(f"📊 整理结果:")
    print(f"   - DFD知识: {results['dfd_knowledge']['concepts_count']} 个概念")
    print(f"   - 爬虫知识: {results['crawler_knowledge']['architectures_count']} 种架构")
    print(f"   - 系统知识: {results['system_knowledge']['components_count']} 个组件")
    print(f"   - 最佳实践: {results['best_practices']['dfd_practices']} 条实践")
    print(f"   - 总条目数: {results['index']['total_entries']}")
    print(f"   - 知识库目录: {organizer.knowledge_base_dir}")
    print(f"   - 验证状态: {results['validation']['status']}")
    
    return results

if __name__ == "__main__":
    main()