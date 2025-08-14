import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

class FormatProcessor:
    """通用格式处理器，根据配置文件动态生成JSON和Markdown格式"""
    
    def __init__(self, format_type: str = "dfd", config_file: str = None):
        if config_file is None:
            # 默认使用DFD格式配置文件
            config_dir = os.path.join(os.path.dirname(__file__), "config")
            config_file = os.path.join(config_dir, "format_templates.json")
        
        self.config_file = Path(config_file)
        self.format_type = format_type
        self.templates = self._load_templates()
        
        # 获取指定格式的模板
        if format_type in self.templates:
            self.template = self.templates[format_type]
        else:
            logger.warning(f"格式类型未找到: {format_type}，将使用默认配置")
            default_templates = self._get_default_template()
            self.templates.update(default_templates)
            self.template = default_templates["dfd"]
        
        self.format_name = self.template.get("format_name", "DFD知识库")
    
    def _load_templates(self) -> Dict:
        """加载格式模板配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件未找到: {self.config_file}，将使用默认配置")
            return self._get_default_template()
        except json.JSONDecodeError as e:
            logger.warning(f"配置文件格式错误: {e}，将使用默认配置")
            return self._get_default_template()
    
    def _get_default_template(self) -> Dict:
        """返回默认的DFD格式模板"""
        return {
            "dfd": {
                "format_name": "DFD知识库",
                "description": "数据流图知识库的结构化数据格式",
                "version": "1.0.0",
                "json_structure": {
                    "metadata": {
                        "title": "string",
                        "source_url": "string",
                        "source_title": "string",
                        "crawl_time": "string"
                    },
                    "knowledge_categories": [
                        {"key": "dfd_concepts", "description": "DFD概念定义"},
                        {"key": "dfd_rules", "description": "DFD规则库"},
                        {"key": "dfd_patterns", "description": "DFD模式库"},
                        {"key": "dfd_cases", "description": "DFD案例库"},
                        {"key": "dfd_nlp_mappings", "description": "DFD自然语言映射"}
                    ]
                },
                "markdown_template": {
                    "header": {
                        "title": "# 📚 {topic}知识库提取结果：{title}",
                        "metadata": [
                            "> 来源：[{title}]({source_url})",
                            "> 抓取时间：{crawl_time_human}",
                            "> 提取方法：{extraction_method}"
                        ]
                    },
                    "sections": [
                        {
                            "title": "## 📊 知识库统计",
                            "content": [
                                "- **概念定义**: {concepts_count} 个",
                                "- **规则条目**: {rules_count} 个",
                                "- **模式模板**: {patterns_count} 个",
                                "- **案例示例**: {cases_count} 个",
                                "- **NLP映射**: {mappings_count} 个"
                            ]
                        }
                    ]
                },
                "extraction_config": {
                    "concepts": {
                        "patterns": {
                            "process": {"keywords": ["处理", "加工", "过程"], "symbol": "圆形"},
                            "entity": {"keywords": ["外部实体", "实体", "用户"], "symbol": "矩形"},
                            "data_store": {"keywords": ["数据存储", "数据库"], "symbol": "平行线"},
                            "data_flow": {"keywords": ["数据流", "箭头"], "symbol": "箭头"}
                        }
                    },
                    "rules": {
                        "hierarchy": {"keywords": ["层次", "分层"], "description": "分层结构规则"},
                        "connection": {"keywords": ["连接", "流向"], "description": "连接规则"}
                    },
                    "system_types": {
                        "电商系统": ["电商", "订单"],
                        "管理系统": ["管理", "信息系统"]
                    },
                    "case_keywords": {
                        "error": ["错误", "问题"],
                        "best_practice": ["正确", "建议"]
                    }
                }
            }
        }
    
    def get_format_name(self) -> str:
        """获取当前格式名称"""
        return self.format_name
    
    def get_available_formats(self) -> List[str]:
        """获取所有可用的格式类型"""
        if hasattr(self, 'templates') and self.templates:
            return list(self.templates.keys())
        return [self.format_type] if hasattr(self, 'format_type') else []
    
    def get_format_info(self, format_type: str) -> Dict:
        """获取指定格式的信息"""
        if hasattr(self, 'templates') and self.templates:
            return self.templates.get(format_type, {})
        return self.template if format_type == self.format_type else {}
    
    def extract_knowledge(self, content: str, url: str = "", title: str = "") -> Dict:
        """根据配置文件提取知识库数据"""
        extracted_data = {}
        
        # 从配置文件中获取知识库类别
        knowledge_categories = self.template.get('json_structure', {}).get('knowledge_categories', [])
        extraction_config = self.template.get('extraction_config', {})
        
        # 为每个知识库类别提取数据
        for category in knowledge_categories:
            category_key = category.get('key')
            if category_key:
                extracted_data[category_key] = self._extract_by_category(content, category_key, extraction_config, url, title)
        
        return extracted_data
    
    def _extract_by_category(self, content: str, category_key: str, extraction_config: Dict, url: str = "", title: str = "") -> List[Dict]:
        """根据配置文件通用提取方法"""
        extracted_items = []
        
        if category_key == 'dfd_concepts':
            extracted_items = self._extract_concepts_from_config(content, extraction_config)
        elif category_key == 'dfd_rules':
            extracted_items = self._extract_rules_from_config(content, extraction_config)
        elif category_key == 'dfd_patterns':
            extracted_items = self._extract_patterns_from_config(content, extraction_config, url, title)
        elif category_key == 'dfd_cases':
            extracted_items = self._extract_cases_from_config(content, extraction_config)
        elif category_key == 'dfd_nlp_mappings':
            extracted_items = self._extract_nlp_mappings_from_config(content, extraction_config)
        
        return extracted_items
    
    def _extract_concepts_from_config(self, content: str, extraction_config: Dict) -> List[Dict]:
        """从配置文件提取DFD概念定义"""
        concepts = []
        concept_patterns = extraction_config.get('concepts', {}).get('patterns', {})
        
        concept_id = 1
        for element_type, info in concept_patterns.items():
            keywords = info.get('keywords', [])
            symbol = info.get('symbol', '')
            
            for keyword in keywords:
                if keyword in content:
                    concepts.append({
                        'id': f"{element_type[:4]}-{concept_id:03d}",
                        'type': element_type,
                        'description': f"{keyword}相关的DFD元素定义",
                        'symbol': symbol,
                        'rules': [f"{keyword}的使用规则和约定"]
                    })
                    concept_id += 1
                    break
        
        return concepts
    
    def _extract_rules_from_config(self, content: str, extraction_config: Dict) -> List[Dict]:
        """从配置文件提取DFD规则"""
        rules = []
        rule_config = extraction_config.get('rules', {})
        rule_id = 1
        
        for rule_category, rule_info in rule_config.items():
            keywords = rule_info.get('keywords', [])
            description = rule_info.get('description', '')
            
            if any(keyword in content for keyword in keywords):
                rules.append({
                    'id': f'{rule_category[:2]}-{rule_id:02d}',
                    'category': rule_category,
                    'description': description,
                    'condition': f'{rule_category}_condition',
                    'validation': f'check_{rule_category}_rules()'
                })
                rule_id += 1
        
        return rules
    
    def _extract_patterns_from_config(self, content: str, extraction_config: Dict, url: str = "", title: str = "") -> List[Dict]:
        """从配置文件提取DFD模式"""
        patterns = []
        system_types = extraction_config.get('system_types', {})
        
        # 根据内容推断系统类型
        system_type = "通用系统"
        for sys_name, keywords in system_types.items():
            if any(keyword in content for keyword in keywords):
                system_type = sys_name
                break
        
        if any(keyword in content for keyword in ["系统", "流程", "处理"]):
            patterns.append({
                'system': system_type,
                'level': 0,
                'processes': [{'id': 'P1', 'name': f'{system_type}核心处理'}],
                'entities': [{'id': 'E1', 'name': '用户'}],
                'data_stores': [{'id': 'D1', 'name': '数据库'}],
                'flows': [{'from': 'E1', 'to': 'P1', 'data': '输入数据'}]
            })
        
        return patterns
    
    def _extract_cases_from_config(self, content: str, extraction_config: Dict) -> List[Dict]:
        """从配置文件提取DFD案例"""
        cases = []
        case_keywords = extraction_config.get('case_keywords', {})
        case_id = 1
        
        # 检测错误案例关键词
        error_keywords = case_keywords.get('error', [])
        best_practice_keywords = case_keywords.get('best_practice', [])
        
        if any(keyword in content for keyword in error_keywords):
            cases.append({
                'id': f'case-err-{case_id:03d}',
                'type': 'error_case',
                'description': '从网页内容中识别的DFD绘制错误案例',
                'incorrect': {'elements': ['错误的元素连接'], 'flows': ['不规范的数据流']},
                'correct': {'elements': ['正确的元素连接'], 'flows': ['规范的数据流']},
                'explanation': '基于网页内容总结的错误原因和改正方法'
            })
            case_id += 1
        
        if any(keyword in content for keyword in best_practice_keywords):
            cases.append({
                'id': f'case-best-{case_id:03d}',
                'type': 'best_practice',
                'description': '从网页内容中提取的DFD最佳实践',
                'incorrect': {},
                'correct': {'elements': ['推荐的元素设计'], 'flows': ['标准的数据流设计']},
                'explanation': '基于网页内容总结的最佳实践要点'
            })
            case_id += 1
        
        return cases
    
    def _extract_nlp_mappings_from_config(self, content: str, extraction_config: Dict) -> List[Dict]:
        """从配置文件提取DFD NLP映射"""
        mappings = []
        
        # 基于内容检测常见的NLP模式
        if any(keyword in content for keyword in ['用户', '系统', '操作', '处理']):
            mappings.extend([
                {
                    'pattern': '用户 [action] 系统',
                    'element_type': 'data_flow',
                    'name_template': '{用户}到{系统}的{action}',
                    'flow_template': '{action}请求',
                    'action_mappings': {'提交': '输入', '查询': '请求', '修改': '更新'}
                },
                {
                    'pattern': '系统 [action] 数据库',
                    'element_type': 'data_flow',
                    'name_template': '{系统}对{数据库}的{action}',
                    'flow_template': '{action}操作',
                    'action_mappings': {'存储': '写入', '读取': '查询', '删除': '移除'}
                }
            ])
        
        return mappings
    

    
    def generate_json_structure(self, extracted_data: Dict, url: str, title: str) -> Dict:
        """根据配置生成JSON结构"""
        # 构建元数据
        metadata = {
            "source_url": url,
            "source_title": title,
            "crawl_time": datetime.now().isoformat(),
            "extraction_method": "基于配置文件的自动提取",
            "topic": "DFD"
        }
        
        categories = self.template["json_structure"]["knowledge_categories"]
        
        # 构建JSON结构
        json_obj = {
            "metadata": metadata,
            "statistics": {}
        }
        
        # 根据配置添加各个知识类别
        for category in categories:
            key = category["key"]
            if key in extracted_data:  # 直接匹配完整的key
                json_obj[key] = extracted_data[key]
                json_obj["statistics"][f"{key.split('_')[-1]}_count"] = len(extracted_data[key])
            else:
                json_obj[key] = []
                json_obj["statistics"][f"{key.split('_')[-1]}_count"] = 0
        
        return json_obj
    
    def generate_markdown(self, extracted_data: Dict, metadata: Dict) -> str:
        """根据配置生成Markdown格式"""
        content_analysis = metadata.get('content_analysis', '内容分析结果')
        
        template = self.template["markdown_template"]
        md_lines = []
        
        # 生成标题和元数据
        title_template = template["header"]["title"]
        md_lines.append(self._format_template(title_template, metadata))
        
        for meta_line in template["header"]["metadata"]:
            md_lines.append(self._format_template(meta_line, metadata))
        
        md_lines.append("")
        
        # 生成各个部分
        for section in template["sections"]:
            md_lines.append(section["title"])
            
            if "content" in section:
                if isinstance(section["content"], str):
                    md_lines.append(self._format_template(section["content"], {**metadata, "content_analysis": content_analysis}))
                elif isinstance(section["content"], list):
                    for line in section["content"]:
                        # 从配置文件动态获取知识库类别
                        categories = self.template["json_structure"]["knowledge_categories"]
                        stats = {f"{category['key'].split('_')[-1]}_count": len(extracted_data.get(category['key'], [])) 
                                for category in categories}
                        md_lines.append(self._format_template(line, stats))
            
            if "description" in section:
                md_lines.append(section["description"])
            
            # 处理数据项
            if "item_template" in section:
                section_key = section["title"].split("(")[-1].split(")")[0] if "(" in section["title"] else ""
                data_key = section_key if section_key in extracted_data else ""
                
                if data_key in extracted_data and extracted_data[data_key]:
                    for item in extracted_data[data_key]:
                        # 生成项目标题
                        header = self._format_template(section["item_template"]["header"], item)
                        md_lines.append(header)
                        
                        # 生成项目字段
                        for field_template in section["item_template"]["fields"]:
                            # 处理特殊字段（如数组连接）
                            item_data = item.copy()
                            if "rules_joined" in field_template and "rules" in item:
                                item_data["rules_joined"] = ", ".join(item["rules"])
                            if "processes_count" in field_template and "processes" in item:
                                item_data["processes_count"] = len(item["processes"])
                            if "entities_count" in field_template and "entities" in item:
                                item_data["entities_count"] = len(item["entities"])
                            if "data_stores_count" in field_template and "data_stores" in item:
                                item_data["data_stores_count"] = len(item["data_stores"])
                            if "flows_count" in field_template and "flows" in item:
                                item_data["flows_count"] = len(item["flows"])
                            
                            md_lines.append(self._format_template(field_template, item_data))
                        md_lines.append("")
                else:
                    md_lines.append(section["empty_message"])
            
            md_lines.append("")
        
        # 生成页脚
        if "footer" in template:
            md_lines.append(template["footer"]["title"])
            for line in template["footer"]["content"]:
                md_lines.append(line)
        
        return "\n".join(md_lines)
    
    def _format_template(self, template: str, data: Dict) -> str:
        """格式化模板字符串"""
        try:
            return template.format(**data)
        except KeyError as e:
            # 如果缺少某个键，返回原始模板
            return template
    
    def reload_templates(self):
        """重新加载模板配置"""
        templates = self._load_templates()
        if self.format_type in templates:
            self.template = templates[self.format_type]
        else:
            self.template = self._get_default_template()["dfd"]
    
    def add_format_template(self, format_type: str, template_config: Dict):
        """添加新的格式模板"""
        templates = self._load_templates()
        templates[format_type] = template_config
        
        # 保存到配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
    
    def update_format_template(self, format_type: str, template_config: Dict):
        """更新现有格式模板"""
        templates = self._load_templates()
        if format_type not in templates:
            raise ValueError(f"格式类型不存在: {format_type}")
        
        templates[format_type].update(template_config)
        
        # 保存到配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
    
    def save_knowledge_base(self, data: Dict, base_filename: str = None, output_dir: str = "shared_data/knowledge_base") -> Dict:
        """根据格式配置保存知识库数据到独立文件"""
        try:
            from datetime import datetime as _dt
            
            # 生成文件名前缀
            if not base_filename:
                timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
                base_filename = f"{self.format_type}_knowledge_{timestamp}"
            
            # 创建知识库目录
            kb_dir = Path(output_dir)
            kb_dir.mkdir(parents=True, exist_ok=True)
            
            saved_files = []
            
            # 获取知识分类配置
            knowledge_categories = self.template.get("json_structure", {}).get("knowledge_categories", [])
            
            # 根据配置保存每个分类的数据
            for category in knowledge_categories:
                category_key = category["key"]
                category_name = category["name"]
                category_desc = category["description"]
                category_fields = category.get("fields", {})
                
                if category_key in data and data[category_key]:
                    # 生成文件路径
                    file_path = kb_dir / f"{base_filename}_{category_key.replace('dfd_', '')}.json"
                    
                    # 构建数据结构
                    category_data = {
                        "table_name": category_key,
                        "description": category_desc,
                        "schema": self._generate_schema_from_fields(category_fields),
                        "data": data[category_key],
                        "metadata": data.get('metadata', {})
                    }
                    
                    # 保存文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(category_data, f, ensure_ascii=False, indent=2)
                    
                    saved_files.append(str(file_path))
            
            # 生成汇总报告
            summary_file = kb_dir / f"{base_filename}_summary.json"
            summary_data = {
                "extraction_summary": {
                    "source_url": data.get('metadata', {}).get('source_url', ''),
                    "extraction_time": _dt.now().isoformat(),
                    "total_files_saved": len(saved_files),
                    "statistics": data.get('statistics', {})
                },
                "saved_files": saved_files,
                "knowledge_base_structure": {cat["key"]: cat["description"] for cat in knowledge_categories}
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "saved_files": saved_files,
                "summary_file": str(summary_file),
                "statistics": data.get('statistics', {})
            }
            
        except Exception as e:
            logger.error(f"保存知识库数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_schema_from_fields(self, fields: Dict) -> Dict:
        """根据字段配置生成数据库模式"""
        schema = {}
        for field_name, field_type in fields.items():
            if field_type == "string":
                schema[field_name] = "text"
            elif field_type == "integer":
                schema[field_name] = "int"
            elif field_type == "array":
                schema[field_name] = "jsonb (数组)"
            elif field_type == "object":
                schema[field_name] = "jsonb (对象)"
            else:
                schema[field_name] = f"text ({field_type})"
        return schema

# 使用示例
if __name__ == "__main__":
    processor = FormatProcessor()
    
    # 查看可用格式
    logger.info("可用格式: %s", processor.get_available_formats())
    
    # 查看DFD格式信息
    logger.info("DFD格式信息: %s", processor.get_format_info("dfd"))
    
    # 模拟提取数据
    sample_content = "这是关于数据流图的内容，包含处理过程、外部实体、数据存储等概念。"
    extracted = processor.extract_knowledge(sample_content, "https://example.com", "测试页面")
    logger.info("提取的数据: %s", extracted)
    
    # 测试生成JSON和Markdown
    metadata = {
        "source_url": "https://example.com",
        "title": "测试页面",
        "crawl_time": datetime.now().isoformat(),
        "crawl_time_human": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "extraction_method": "基于配置文件的自动提取",
        "topic": "DFD",
        "content_analysis": "这是内容分析结果"
    }
    
    json_result = processor.generate_json_structure(extracted, "https://example.com", "测试页面")
    logger.info("JSON结构: %s", json.dumps(json_result, ensure_ascii=False, indent=2))
    
    # 测试Markdown生成
    md_result = processor.generate_markdown(extracted, metadata)
    logger.info("Markdown结果:")
    logger.info(md_result)