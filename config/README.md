# 格式配置系统使用指南

## 概述

本系统将网页抓取后的信息整理格式从硬编码改为配置文件驱动，支持通过修改配置文件来定制不同类型知识库的输出格式。

## 文件结构

```
config/
├── format_templates.json      # DFD知识库格式配置（默认）
├── uml_format_templates.json  # UML知识库格式配置（示例）
├── format_processor.py        # 格式处理器核心类
└── README.md                  # 本说明文档
```

## 配置文件结构

每个格式配置文件包含以下主要部分：

### 1. 基本信息
```json
{
  "format_name": "知识库名称",
  "description": "格式描述",
  "version": "版本号"
}
```

### 2. JSON结构定义
```json
{
  "json_structure": {
    "metadata": {
      "title": "string",
      "source_url": "string",
      // ... 其他元数据字段
    },
    "knowledge_categories": {
      "category_name": {
        "description": "分类描述",
        "fields": {
          "field_name": "field_type"
        }
      }
    }
  }
}
```

### 3. Markdown模板定义
```json
{
  "markdown_template": {
    "title": "# 标题模板",
    "metadata_section": {
      "title": "## 元数据标题",
      "content": ["模板行1", "模板行2"]
    },
    "categories": {
      "category_name": {
        "title": "## 分类标题",
        "description": "分类描述",
        "item_template": ["项目模板行"],
        "empty_message": "空数据提示"
      }
    }
  }
}
```

## 使用方法

### 1. 创建新的格式配置

1. 复制现有的配置文件（如 `format_templates.json`）
2. 修改基本信息和格式名称
3. 定义新的知识分类和字段结构
4. 设计对应的Markdown输出模板
5. 保存为新的配置文件

### 2. 在代码中使用

```python
# 初始化格式处理器（默认使用format_templates.json）
format_processor = FormatProcessor()

# 或指定特定的配置文件
format_processor = FormatProcessor('config/uml_format_templates.json')

# 提取知识数据
knowledge_data = format_processor.extract_knowledge(content, url, title)

# 生成JSON结构
json_structure = format_processor.generate_json_structure(knowledge_data, metadata)

# 生成Markdown内容
markdown_content = format_processor.generate_markdown(knowledge_data, metadata)
```

### 3. 模板变量说明

在Markdown模板中可以使用以下变量：

- `{title}` - 主题标题
- `{source_url}` - 来源URL
- `{source_title}` - 来源标题
- `{crawl_time}` - 抓取时间
- `{content_analysis}` - 内容分析
- `{category_name_count}` - 各分类的数量统计
- 字段变量：`{field_name}` - 对应字段的值
- 列表变量：`{field_name_list}` - 数组字段的逗号分隔字符串

## 配置示例

### DFD知识库配置
- 文件：`format_templates.json`
- 包含：概念定义、规则条目、模式模板、案例示例、NLP映射

### UML知识库配置
- 文件：`uml_format_templates.json`
- 包含：UML图表、设计模式、建模规则、符号指南、最佳实践

## 扩展指南

### 添加新的知识分类

1. 在 `json_structure.knowledge_categories` 中添加新分类
2. 定义分类的字段结构
3. 在 `markdown_template.categories` 中添加对应的输出模板
4. 在 `FormatProcessor` 类中添加对应的提取逻辑（如需要）

### 修改输出格式

1. 调整 `markdown_template` 中的模板结构
2. 修改标题、描述和项目模板
3. 更新变量占位符

### 自定义提取逻辑

如果需要特殊的内容提取逻辑，可以：

1. 继承 `FormatProcessor` 类
2. 重写 `extract_knowledge` 方法
3. 实现自定义的提取算法

## 注意事项

1. **配置文件格式**：必须是有效的JSON格式
2. **字段类型**：支持 string、array、object 等基本类型
3. **模板变量**：确保模板中使用的变量在数据中存在
4. **编码格式**：配置文件使用UTF-8编码
5. **向后兼容**：修改现有配置时注意保持向后兼容性

## 故障排除

### 常见问题

1. **配置文件加载失败**
   - 检查JSON格式是否正确
   - 确认文件路径是否存在
   - 验证文件编码是否为UTF-8

2. **模板渲染错误**
   - 检查模板变量是否正确
   - 确认数据结构与模板匹配
   - 验证数组字段的处理逻辑

3. **知识提取不准确**
   - 调整关键词匹配规则
   - 优化提取算法
   - 增加更多的模式识别

## 更新日志

- **v1.0.0** - 初始版本，支持DFD和UML格式配置
- 后续版本将根据需求添加更多功能和格式支持