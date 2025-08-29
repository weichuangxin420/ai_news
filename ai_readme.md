# AI新闻收集与影响分析系统 - 项目结构说明

## 📋 项目概述

AI新闻收集与影响分析系统是一个基于Python的自动化新闻分析平台，集成了新闻收集、AI分析、深度分析和邮件报告等功能。系统使用OpenRouter API调用DeepSeek AI模型，对财经新闻进行智能分析和影响评估。

## 🏗️ 项目架构

```
ai_news/
├── 📁 config/                    # 配置文件目录
│   ├── config.yaml              # 主配置文件
│   └── config.yaml.template     # 配置文件模板
├── 📁 data/                     # 数据存储目录
│   ├── logs/                    # 日志文件
│   └── news.db                  # SQLite数据库
├── 📁 src/                      # 源代码目录
│   ├── __init__.py
│   ├── 📁 ai/                   # AI分析模块
│   │   ├── __init__.py
│   │   ├── ai_analyzer.py       # AI影响分析器
│   │   ├── importance_analyzer.py # 重要性分析器
│   │   ├── deep_analyzer.py     # 深度分析器
│   │   └── 📁 ai_tools/         # AI工具集
│   │       ├── __init__.py
│   │       ├── baidu_search.py  # 百度搜索工具
│   │       └── methods.py       # 通用方法
│   ├── 📁 collectors/           # 新闻收集模块
│   │   ├── __init__.py
│   │   ├── chinanews_rss.py     # 中国新闻网RSS收集器
│   │   └── news_collector.py    # 新闻收集器主类
│   ├── 📁 utils/                # 工具模块
│   │   ├── __init__.py
│   │   ├── database.py          # 数据库管理
│   │   └── logger.py            # 日志管理
│   ├── config_manager.py        # 配置管理器
│   ├── email_sender.py          # 邮件发送器
│   └── scheduler.py             # 任务调度器
├── 📁 test/                     # 测试模块目录
│   ├── __init__.py
│   ├── main_test.py             # 主测试文件
│   ├── test_ai_analysis.py      # AI分析测试
│   ├── test_api.py              # API测试
│   ├── test_database.py         # 数据库测试
│   ├── test_deep_analysis.py    # 深度分析测试
│   ├── test_deepseek_search.py  # DeepSeek搜索测试
│   ├── test_email.py            # 邮件功能测试
│   ├── test_news_collection.py  # 新闻收集测试
│   ├── test_openrouter_api.py   # OpenRouter API测试
│   └── 📁 data/                 # 测试数据
├── docker-compose.yml            # Docker编排文件
├── Dockerfile                    # Docker镜像文件
├── main.py                       # 主程序入口
├── PRD.md                        # 产品需求文档
├── README.md                     # 项目说明文档
├── requirements.txt              # Python依赖包
└── ai_readme.md                  # 本文件 - AI项目结构说明
```

config.yaml 是真实的配置文件
config.yaml.template 是配置文件模板

`src/ai/ai_analyzer.py`
- **`__init__(config_path, provider)`** - 初始化AI分析器，支持OpenRouter和DeepSeek API
- **`_load_config(config_path)`** - 加载YAML配置文件
- **`_setup_client()`** - 设置OpenAI客户端，配置API密钥和基础URL
- **`analyze_news(news_item)`** - 分析单条新闻（支持失败重试和备用模型调用），返回影响评分和摘要
- **`analyze_news_batch(news_items, max_workers)`** - 并行批量分析多条新闻
- **`_build_analysis_prompt(news_item)`** - 构建AI分析提示词
- **`_call_ai_api(prompt)`** - 调用AI API进行分析
- **`_call_ai_api_with_fallback(prompt)`** - 使用备用客户端调用AI API，支持备用模型
- **`_setup_fallback_client(ai_config, extra_headers)`** - 设置备用客户端，使用备用模型配置
- **`_parse_analysis_response(news_id, response)`** - 解析AI API响应结果
- **`_save_analysis_result(result)`** - 保存分析结果到SQLite数据库
- **`format_analysis_report(results)`** - 格式化分析报告为Markdown格式
- **`get_stats()`** - 获取分析器统计信息
- **`AnalysisResult`** - 分析结果数据类，包含新闻ID、影响评分、摘要、分析时间

`src/ai/importance_analyzer.py`
- **`__init__(config)`** - 初始化重要性分析器，加载配置并初始化OpenRouter客户端
- **`_load_config()`** - 加载YAML配置文件
- **`_init_client()`** - 初始化OpenRouter客户端，配置API密钥和基础URL
- **`analyze_importance(news_item)`** - 分析单条新闻的重要程度，返回0-100分评分
- **`batch_analyze_importance(news_list)`** - 批量分析新闻重要程度，支持延时避免API限制
- **`_build_importance_prompt(news_item)`** - 构建重要性分析的prompt，包含评分标准和分析要求
- **`_call_thinking_model(prompt)`** - 调用DeepSeek思考模型进行重要性分析
- **`_parse_importance_result(news_item, response)`** - 解析重要性分析结果，提取分数、推理过程和关键因素
- **`_parse_text_result(response)`** - 解析纯文本格式的结果，尝试提取分数信息
- **`_mock_analysis(news_item, error)`** - 模拟分析结果，用于测试或API不可用时的降级处理

`src/ai/deep_analyzer.py`
- **`__init__(config)`** - 初始化深度分析器，加载配置并初始化OpenRouter客户端
- **`_load_config()`** - 加载YAML配置文件
- **`_init_client()`** - 初始化OpenRouter客户端，配置API密钥和基础URL
- **`should_analyze(news_item)`** - 判断是否需要进行深度分析（重要性分数≥70分）
- **`analyze_news_deep(news_item)`** - 对单条新闻进行深度分析，选择AI自驱动或传统模式
- **`batch_analyze_deep(news_list)`** - 批量深度分析新闻，使用线程池并发处理
- **`_analyze_with_ai_self_search(news_item)`** - 使用AI自驱动检索模式进行深度分析
- **`_analyze_with_keyword_search(news_item)`** - 使用传统关键词检索模式进行深度分析
- **`_generate_search_queries(news_item)`** - AI生成检索查询列表，基于新闻内容智能规划
- **`_parse_search_queries(response)`** - 解析AI生成的搜索查询响应
- **`_perform_single_search(query)`** - 执行单次搜索，调用百度搜索工具
- **`_evaluate_and_summarize_evidence(search_results, news_item)`** - 评估和汇总搜索证据，计算质量分数
- **`_calculate_evidence_score(result, query, news_item)`** - 计算单个证据的质量分数（权威度、相关度、信息密度等）
- **`_create_evidence_summary(top_evidence, news_item)`** - 创建证据汇总，格式化高质量证据
- **`_generate_evidence_based_analysis(news_item, evidence_summary)`** - 基于证据生成深度分析报告
- **`_adjust_score_with_evidence(news_item, deep_analysis, evidence_summary)`** - 基于证据和深度分析调整重要性分数
- **`_extract_search_keywords(news_item)`** - 从新闻中提取搜索关键词
- **`_extract_keywords_from_text(text)`** - 从文本中提取关键词，识别财经相关术语
- **`_perform_search(keywords, title)`** - 执行百度搜索，保持向后兼容
- **`_generate_deep_analysis(news_item, search_results, keywords)`** - 生成深度分析报告，保持向后兼容
- **`_build_deep_analysis_prompt(news_item, search_results, keywords)`** - 构建深度分析的prompt
- **`_call_ai_model(prompt)`** - 调用AI模型进行分析，支持深度分析专属max_tokens
- **`_parse_analysis_response(response)`** - 解析AI分析响应，清理和格式化
- **`_adjust_importance_score(news_item, deep_analysis, search_results)`** - 根据深度分析调整重要性分数
- **`_generate_mock_analysis(news_item, search_results, keywords)`** - 生成模拟深度分析报告
- **`_create_skip_result(news_item)`** - 创建跳过分析的结果
- **`_create_error_result(news_item, error_msg)`** - 创建错误结果

`src/ai/ai_tools/baidu_search.py`
- **`__init__(user_agent)`** - 初始化百度搜索API，设置请求头和基础URL
- **`search(query, max_results)`** - 执行百度网页搜索，解析结果并返回结构化数据
- **`simple_search(query)`** - 简单搜索方法，返回搜索URL和基本信息
- **`baidu_search_tool(query, max_results)`** - 专门用于Function Call的百度搜索工具，返回AI友好的格式化结果
- **`get_baidu_search_tool_definition()`** - 获取百度搜索工具的Function Call定义，符合OpenAI规范
- **`register_baidu_search_tool(executor)`** - 注册百度搜索工具到执行器
- **`create_search_tools_list()`** - 创建包含百度搜索的工具列表
- **`test_baidu_search()`** - 简单测试函数，验证搜索功能

`src/ai/ai_tools/methods.py`
- **`__init__()`** - 初始化工具执行器，管理工具注册和执行
- **`register_tool(name, func, description, parameters)`** - 注册工具到执行器
- **`unregister_tool(name)`** - 取消注册工具
- **`get_tool_definitions()`** - 获取所有工具的定义，用于API调用
- **`get_tool_names()`** - 获取所有已注册的工具名称
- **`has_tool(name)`** - 检查是否存在指定工具
- **`execute_tool(name, arguments)`** - 执行指定工具，返回执行结果
- **`execute_multiple_tools(tool_calls)`** - 批量执行多个工具
- **`get_execution_history(limit)`** - 获取执行历史记录
- **`clear_history()`** - 清空执行历史
- **`get_stats()`** - 获取执行统计信息
- **`execute_function_call(tool_name, arguments, executor)`** - 执行Function Call，支持工具调用
- **`execute_multiple_function_calls(tool_calls, executor)`** - 批量执行多个Function Call
- **`format_tool_response(result, include_metadata)`** - 格式化工具响应结果
- **`format_multiple_tool_responses(results, include_metadata)`** - 格式化多个工具响应结果
- **`create_tool_definition(name, description, parameters)`** - 创建工具定义
- **`validate_tool_arguments(parameters, arguments)`** - 验证工具参数
- **`make_http_request(url, method, headers, params, data, timeout, allow_redirects)`** - 执行HTTP请求的基础方法
- **`get_default_headers(user_agent)`** - 获取默认HTTP请求头
- **`register_tool_from_function(func, name, description, parameters, executor)`** - 从函数自动注册工具
- **`call_openai_with_tools(client, user_message, tools, model, max_tokens, temperature, system_message, executor)`** - 调用OpenAI兼容API并支持Function Call工具调用
- **`execute_tool_call_by_name(tool_name, tool_args, executor)`** - 根据工具名称执行工具调用

`src/collectors/chinanews_rss.py`
- **`__init__()`** - 初始化中国新闻网RSS收集器，设置请求头和超时时间
- **`fetch_news(max_items)`** - 获取财经新闻，解析RSS内容并返回新闻列表
- **`_parse_entry(entry)`** - 解析RSS条目，提取标题、链接、发布时间、摘要等信息
- **`_parse_time(entry)`** - 解析发布时间，支持多种时间字段格式
- **`_clean_html(text)`** - 清理HTML标签，解码HTML实体，清理多余空白字符
- **`test_connection()`** - 测试RSS连接，验证网络连接和内容解析

`src/collectors/news_collector.py`
- **`__init__(config_path)`** - 初始化新闻收集器主类，加载配置并设置请求参数
- **`_load_config(config_path)`** - 加载YAML配置文件
- **`collect_all_news()`** - 从中国新闻网RSS源收集财经新闻，执行去重和保存
- **`_collect_rss_news(rss_feeds)`** - 收集RSS新闻，支持多源并发收集
- **`_fetch_rss_feed(feed_config)`** - 获取单个RSS源的新闻，解析RSS内容
- **`_collect_api_news(api_sources)`** - 收集API新闻，支持东方财富、腾讯财经、新浪财经等
- **`_fetch_eastmoney_news(config)`** - 获取东方财富新闻数据，解析JSONP格式
- **`_fetch_tencent_news(config)`** - 获取腾讯财经数据，解析股票指数信息
- **`_fetch_sina_news(config)`** - 获取新浪财经数据，解析股市行情信息
- **`_format_stock_data(item)`** - 格式化股票数据为新闻内容
- **`_collect_web_news(web_sources)`** - 收集网页爬虫新闻，谨慎使用避免被封
- **`_scrape_website(source)`** - 爬取单个网站，使用BeautifulSoup解析HTML
- **`_extract_content_from_entry(entry)`** - 从RSS条目中提取内容，清理HTML标签
- **`_parse_time_string(time_str)`** - 解析时间字符串，支持多种格式
- **`_generate_simple_tags(title, content)`** - 生成简单标签，基于常见财经术语
- **`_deduplicate_news(news_list)`** - 新闻去重，移除重复标题和数据库重复项
- **`_log_stats()`** - 记录统计信息，包括收集数量、重复数量、错误数量等
- **`_convert_to_news_item(news_data)`** - 将RSS收集器的数据格式转换为NewsItem
- **`get_stats()`** - 获取收集器统计信息
- **`collect_news()`** - 便捷函数，收集新闻并返回结果

`src/utils/database.py`
- **`__init__(db_path)`** - 初始化数据库管理器，确保数据库目录存在并初始化表结构
- **`_ensure_db_dir()`** - 确保数据库目录存在，如果不存在则创建
- **`_init_database()`** - 初始化数据库表结构，创建新闻表和分析结果表，支持增量迁移
- **`save_news_item(news_item)`** - 保存单个新闻项到数据库，自动生成ID
- **`save_news_items_batch(news_items)`** - 批量保存新闻项到数据库，返回成功保存的数量
- **`get_news_items_by_date_range(start_date, end_date)`** - 获取指定日期范围内的新闻，按重要性分数排序
- **`get_news_items(limit, offset, source, category, start_time, end_time)`** - 获取新闻项列表，支持多种过滤条件
- **`get_news_item_by_id(news_id)`** - 根据ID获取新闻项
- **`delete_old_news(days)`** - 删除过期新闻，同时清理相关的分析结果
- **`check_news_exists(title, url)`** - 检查新闻是否已存在，用于去重
- **`get_stats()`** - 获取数据库统计信息，包括总新闻数、今日新闻数、来源统计、分类统计
- **`cleanup_old_data(days)`** - 清理旧数据，删除指定天数前的新闻和分析结果
- **`optimize_database()`** - 优化数据库性能，执行VACUUM和ANALYZE操作
- **`to_dict()`** - 将NewsItem转换为字典格式，支持JSON序列化
- **`from_dict(data)`** - 从字典创建NewsItem对象，处理时间字段和JSON字段
- **`update_with_deep_analysis(deep_analysis_result)`** - 使用深度分析结果更新新闻项

`src/utils/logger.py`
- **`__new__(name, config_path)`** - 单例模式确保每个名称只有一个日志实例
- **`__init__(name, config_path)`** - 初始化日志器，加载配置并设置处理器
- **`_load_config(config_path)`** - 加载YAML配置文件
- **`_setup_handlers()`** - 设置日志处理器，包括控制台和文件处理器
- **`_parse_size(size_str)`** - 解析大小字符串（如'10MB'）为字节数
- **`debug(message)`** - 记录调试信息
- **`info(message)`** - 记录一般信息
- **`warning(message)`** - 记录警告信息
- **`error(message)`** - 记录错误信息
- **`critical(message)`** - 记录严重错误信息
- **`exception(message)`** - 记录异常信息，包含堆栈跟踪
- **`get_logger(name)`** - 获取日志器实例
- **`debug(message)`** - 便捷函数，记录调试信息
- **`info(message)`** - 便捷函数，记录一般信息
- **`warning(message)`** - 便捷函数，记录警告信息
- **`error(message)`** - 便捷函数，记录错误信息
- **`critical(message)`** - 便捷函数，记录严重错误信息
- **`exception(message)`** - 便捷函数，记录异常信息

`src/config_manager.py`
- **`__init__(config_path)`** - 初始化配置管理器，加载、验证和设置默认配置
- **`_find_config_file()`** - 查找配置文件，支持多种路径格式
- **`_load_config()`** - 加载配置文件，处理环境变量替换
- **`_resolve_env_vars(obj)`** - 递归解析环境变量，支持${VAR_NAME}格式
- **`_validate_config()`** - 验证配置文件的完整性，检查必要配置节
- **`_set_defaults()`** - 设置默认值，递归合并用户配置和默认配置
- **`_merge_configs(default, user)`** - 递归合并配置字典，用户配置优先
- **`get(key, default)`** - 获取配置值，支持点号分隔的嵌套键
- **`set(key, value)`** - 设置配置值，支持点号分隔的嵌套键
- **`save(path)`** - 保存配置到文件，确保目录存在
- **`reload()`** - 重新加载配置文件，重新验证和设置默认值
- **`get_news_sources()`** - 获取新闻源配置
- **`get_ai_config()`** - 获取AI配置
- **`get_email_config()`** - 获取邮箱配置
- **`get_database_config()`** - 获取数据库配置
- **`is_source_enabled(source_type, source_name)`** - 检查指定数据源是否启用
- **`get_keywords()`** - 获取关键词配置
- **`validate_api_keys()`** - 验证API密钥是否存在
- **`create_example_config(output_path)`** - 创建示例配置文件，替换敏感信息为占位符

`src/email_sender.py`
- **`__init__(config_path)`** - 初始化邮件发送器，加载配置并设置SMTP参数
- **`_load_config(config_path)`** - 加载YAML配置文件
- **`_resolve_env_vars(obj)`** - 递归解析环境变量
- **`send_analysis_report(analysis_results, recipients, subject)`** - 发送分析报告邮件，生成HTML报告
- **`send_simple_email(recipients, subject, content, is_html)`** - 发送简单邮件，支持HTML和纯文本
- **`_send_email(recipients, subject, html_content, text_content, attachments)`** - 发送邮件的核心方法
- **`_validate_smtp_config()`** - 验证SMTP配置，检查必要字段
- **`_create_smtp_connection()`** - 创建SMTP连接，支持SSL、TLS和不加密连接
- **`_get_from_address()`** - 获取发件人地址，包含发件人名称
- **`_generate_subject()`** - 生成邮件主题，支持模板变量
- **`_generate_html_report(analysis_results)`** - 生成HTML格式的分析报告，包含深度分析信息
- **`_add_attachment(msg, file_path)`** - 添加附件到邮件
- **`test_connection()`** - 测试邮件服务器连接
- **`send_test_email(recipient)`** - 发送测试邮件
- **`get_stats()`** - 获取邮件发送统计信息
- **`send_analysis_report_email(analysis_results, recipients)`** - 便捷函数，发送分析报告邮件

`src/scheduler.py`
- **`__init__(config_path, state_file)`** - 初始化任务调度器，集成管理、监控和错误恢复功能
- **`_load_config(config_path)`** - 加载配置文件
- **`_resolve_env_vars(obj)`** - 递归解析环境变量
- **`_setup_event_listeners()`** - 设置事件监听器，监听任务执行和错误事件
- **`_setup_signal_handlers()`** - 设置信号处理器，优雅关闭
- **`_filter_news_by_score(news_list, min_score)`** - 根据重要性分数过滤新闻
- **`_calculate_news_stats(news_list)`** - 计算新闻统计信息，包括高、中、低重要性数量
- **`_validate_config()`** - 验证配置文件的完整性
- **`_signal_handler(signum, frame)`** - 信号处理器，优雅关闭调度器
- **`_job_executed_listener(event)`** - 任务执行事件监听器，记录执行统计
- **`save_state()`** - 保存调度器状态，包含运行状态、错误统计、执行历史等
- **`load_state()`** - 加载调度器状态，恢复错误统计和执行历史
- **`record_event(event_type, success, message)`** - 记录事件到执行历史
- **`start_monitoring()`** - 启动监控线程
- **`stop_monitoring()`** - 停止监控线程
- **`_monitor_loop()`** - 监控循环，执行健康检查和错误恢复
- **`check_health()`** - 健康检查，评估组件状态和任务执行状态
- **`check_error_recovery()`** - 检查是否需要错误恢复，自动重启调度器
- **`get_dashboard_data()`** - 获取仪表板数据，包含状态、统计、健康信息
- **`_calculate_uptime()`** - 计算运行时间
- **`_get_jobs_info()`** - 获取任务信息
- **`get_status()`** - 获取调度器状态（兼容性方法）
- **`run_with_ui()`** - 运行调度器并显示状态信息，实时监控界面
- **`initialize_components()`** - 初始化组件，包括新闻收集器、AI分析器等
- **`add_news_collection_job(interval_minutes)`** - 添加新闻收集任务
- **`add_analysis_and_email_job(analysis_interval_minutes, email_cron)`** - 添加分析和邮件发送任务
- **`add_full_pipeline_job(interval_minutes)`** - 添加完整流程任务（收集+分析+邮件）
- **`add_enhanced_strategy_jobs()`** - 添加增强版调度策略任务，包括早上收集、交易时间收集、晚上收集、每日汇总
- **`add_maintenance_job()`** - 添加维护任务（数据清理等）
- **`_news_collection_task()`** - 新闻收集任务
- **`_analysis_task()`** - AI分析任务（使用增强版并发分析）
- **`_email_task()`** - 邮件发送任务
- **`_full_pipeline_task()`** - 完整流程任务
- **`_morning_collection_with_email()`** - 早上8点：收集、分析并发送邮件
- **`_trading_hours_collection()`** - 交易时间收集（8:00-16:00）
- **`_evening_collection_no_email()`** - 晚上10点：收集但不发送邮件
- **`_daily_summary_email()`** - 每日汇总邮件（晚上11:30）
- **`_maintenance_task()`** - 维护任务
- **`_cleanup_logs()`** - 清理日志文件
- **`_send_instant_email(news_list, title_prefix)`** - 发送即时新闻邮件
- **`_send_summary_email(report)`** - 发送汇总邮件
- **`_generate_instant_report(news_list)`** - 生成即时新闻报告（HTML格式）
- **`_generate_daily_summary_report(news_list, stats)`** - 生成每日汇总报告（HTML格式）
- **`_health_check()`** - 系统健康检查
- **`start(enable_news_collection, enable_analysis, enable_email, enable_full_pipeline, enable_enhanced_strategy, enable_maintenance, enable_monitoring)`** - 启动调度器（增强版 - 包含监控和错误恢复）
- **`stop()`** - 停止调度器（增强版 - 包含优雅停止）
- **`restart(**kwargs)`** - 重启调度器
- **`wait()`** - 等待调度器停止（兼容性方法）
- **`start_with_recovery(**kwargs)`** - 启动调度器（兼容性方法）
- **`stop_gracefully()`** - 优雅停止调度器（兼容性方法）
- **`restart_scheduler(**kwargs)`** - 重启调度器（兼容性方法）
- **`pause()`** - 暂停调度器
- **`resume()`** - 恢复调度器
- **`run_job_once(job_id)`** - 立即执行指定任务
- **`print_jobs()`** - 打印任务列表
- **`_update_next_execution_time()`** - 更新下次执行时间
- **`get_stats()`** - 获取调度器统计信息
- **`run_forever()`** - 持续运行调度器
- **`create_default_scheduler()`** - 创建默认配置的调度器
- **`create_scheduler_manager(config_path)`** - 创建调度器管理器实例（兼容性别名）

## 🧪 测试模块详解

### 测试框架模块

`test/main_test.py`
- **`__init__()`** - 初始化测试运行器，设置结果存储和时间记录
- **`run_api_tests()`** - 运行API数据源测试，测试各个API源的连接和数据获取
- **`run_news_collection_tests()`** - 运行新闻收集测试，验证新闻收集功能
- **`run_ai_analysis_tests()`** - 运行AI分析测试（核心功能 + OpenRouter），测试AI分析器
- **`run_deep_analysis_tests()`** - 运行深度分析测试，验证深度分析功能
- **`run_database_tests()`** - 运行数据库测试，验证数据库操作功能
- **`run_all_email_tests()`** - 运行所有邮件测试，包括连接测试和发送测试
- **`run_all_tests()`** - 运行所有测试模块，生成综合测试报告
- **`print_final_summary()`** - 打印最终测试摘要，显示各模块测试结果
- **`main()`** - 主函数，解析命令行参数并执行相应测试

`test/test_deep_analysis.py`
- **`setUp()`** - 测试前准备，加载配置文件并创建测试新闻数据
- **`test_deep_analyzer_initialization()`** - 测试深度分析器初始化，验证配置加载
- **`test_should_analyze_logic()`** - 测试是否需要进行深度分析的逻辑判断
- **`test_baidu_search_functionality()`** - 测试百度搜索功能，验证搜索工具集成
- **`test_single_news_deep_analysis()`** - 测试单条新闻深度分析，验证完整分析流程
- **`test_batch_deep_analysis()`** - 测试批量深度分析，验证并发处理能力
- **`_create_test_news()`** - 创建测试新闻数据，包含高重要性和低重要性新闻
- **`run_deep_analysis_tests()`** - 运行深度分析测试套件，执行所有测试用例

`test/test_openrouter_api.py`
- **`setUp()`** - 测试初始化，设置配置文件路径和测试新闻项
- **`test_openrouter_analyzer_initialization()`** - 测试OpenRouter分析器初始化
- **`test_deepseek_analyzer_initialization()`** - 测试DeepSeek分析器初始化
- **`test_openrouter_api_call_mock()`** - 测试OpenRouter API调用（模拟），验证API集成
- **`test_real_openrouter_api_call()`** - 测试真实的OpenRouter API调用，验证实际功能
- **`test_deepseek_api_call_mock()`** - 测试DeepSeek API调用（模拟）
- **`test_real_deepseek_api_call()`** - 测试真实的DeepSeek API调用
- **`test_provider_switching()`** - 测试提供商切换功能，验证多API支持

`test/test_deepseek_search.py`
- **`test_baidu_search_tool_definition()`** - 测试百度搜索工具定义，验证工具配置
- **`test_search_tools_list()`** - 测试搜索工具列表创建，验证工具管理
- **`test_deepseek_function_call_basic()`** - 测试DeepSeek Function Call基础功能（不涉及实际搜索）
- **`test_deepseek_function_call_with_search()`** - 测试DeepSeek Function Call搜索功能，验证搜索集成
- **`test_search_tool_execution()`** - 测试搜索工具执行，验证工具调用机制
- **`test_error_handling()`** - 测试错误处理，验证异常情况下的行为
- **`run_all_deepseek_search_tests()`** - 运行所有DeepSeek搜索测试，执行完整测试套件

`test/test_ai_analysis.py`
- **`__init__()`** - 初始化测试器，设置分析器和结果存储
- **`test_analyzer_initialization()`** - 测试分析器初始化，验证基本功能
- **`test_single_news_analysis()`** - 测试单条新闻分析（基础功能），验证核心分析能力
- **`test_batch_news_analysis()`** - 测试批量新闻分析，验证并发处理
- **`test_analysis_result_format()`** - 测试分析结果格式，验证输出结构
- **`_create_test_news()`** - 创建测试新闻数据，包含多种类型的测试新闻
- **`run_all_ai_analysis_tests()`** - 运行所有AI分析测试，执行完整测试套件

`test/test_api.py`
- **`__init__()`** - 初始化API测试器，加载配置文件
- **`_load_config()`** - 加载配置文件，优先使用实际配置或模板配置
- **`test_all_apis()`** - 测试所有API源，遍历配置中的API源进行测试
- **`_test_single_api(api_name, api_config)`** - 测试单个API源，验证连接和数据获取
- **`_test_eastmoney_api(api_config)`** - 测试东方财富API，验证股票数据获取
- **`_test_tencent_api(api_config)`** - 测试腾讯财经API，验证指数数据获取
- **`_test_sina_api(api_config)`** - 测试新浪财经API，验证股市行情获取
- **`_format_api_response(api_name, data)`** - 格式化API响应，统一输出格式
- **`run_api_tests()`** - 运行API测试，执行完整的API测试流程

`test/test_email.py`
- **`create_test_data()`** - 创建测试数据，包括测试新闻和分析结果
- **`test_smtp_connection()`** - 测试SMTP连接，验证邮件服务器配置
- **`test_email_sender_initialization()`** - 测试邮件发送器初始化，验证配置加载
- **`test_html_report_generation()`** - 测试HTML报告生成，验证报告模板功能
- **`test_email_sending()`** - 测试邮件发送，验证完整的邮件发送流程
- **`test_attachment_handling()`** - 测试附件处理，验证附件添加功能
- **`test_error_handling()`** - 测试错误处理，验证异常情况下的行为
- **`test_email_templates()`** - 测试邮件模板，验证不同模板的生成
- **`run_all_email_tests()`** - 运行所有邮件测试，执行完整测试套件

`test/test_database.py`
- **`__init__()`** - 初始化数据库测试器，设置结果存储
- **`setup_test_database()`** - 设置测试数据库，创建临时数据库文件
- **`cleanup_test_database()`** - 清理测试数据库，恢复原始配置并删除临时文件
- **`test_database_initialization()`** - 测试数据库初始化，验证表结构创建
- **`test_news_item_operations()`** - 测试新闻项操作，验证CRUD功能
- **`test_batch_operations()`** - 测试批量操作，验证批量插入和查询
- **`test_search_and_filter()`** - 测试搜索和过滤，验证查询功能
- **`test_data_cleanup()`** - 测试数据清理，验证过期数据删除
- **`test_database_optimization()`** - 测试数据库优化，验证性能优化功能
- **`run_all_database_tests()`** - 运行所有数据库测试，执行完整测试套件

`test/test_news_collection.py`
- **`__init__()`** - 初始化新闻收集测试器，设置收集器和结果存储
- **`test_collector_initialization()`** - 测试收集器初始化，验证配置加载
- **`test_news_collection()`** - 测试新闻收集功能，验证新闻获取和处理
- **`test_rss_source_connection()`** - 测试RSS源连接，验证RSS源可用性
- **`test_news_filtering()`** - 测试新闻过滤，验证关键词过滤功能
- **`test_news_deduplication()`** - 测试新闻去重，验证重复新闻处理
- **`test_collection_statistics()`** - 测试收集统计，验证统计信息生成
- **`_create_test_news()`** - 创建测试新闻数据，包含多种类型的测试新闻
- **`run_all_news_collection_tests()`** - 运行所有新闻收集测试，执行完整测试套件


