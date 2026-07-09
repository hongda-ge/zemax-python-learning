# D37 文件命名规范

## 1. 总原则

从 D37 开始，项目文件命名统一使用英文、小写、下划线，尽量避免中文、空格、括号和“最终版”等模糊词。

## 2. 每日任务文件

每日任务相关文件使用：
```text
D编号_功能说明.后缀
eg：
D37_tools_spec.md
D37_file_naming_rules.md
D37_tool_design_notes.md


## 3. 长期复用模块
长期复用模块不加 D 编号，只保留功能名称。
示例：
zemax_runner.py
analysis_runner.py
result_analyzer.py
report_generator.py
task_loader.py
task_validator.py
tool_registry.py

原因：这些模块不是某一天的临时作业，而是后续整个项目都会反复调用的核心代码。

## 4.配置文件
配置文件使用：
D编号_功能_config.yaml

示例：
D37_tool_design_config.yaml
D38_tool_registry_config.yaml
D39_validation_config.yaml

## 5.结果文件
结果文件使用：
YYYYMMDD_d编号_内容_v版本.后缀

示例：
20260706_d37_tools_summary_v01.md
20260706_d37_architecture_v01.png
20260706_d37_tool_design_v01.json

## 6.日志文件
每周日志使用：
weekly_log_周数.md
示例：
weekly_log_06.md

## 7.不推荐命名
以后不要使用：
test.py
demo.py
新建文档.md
最终版.md
最终最终版.md
工具.md
文件(1).py
文件(2).py