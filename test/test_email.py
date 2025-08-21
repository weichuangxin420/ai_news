"""
邮件发送功能完整测试
包括模板生成、连接测试、发送测试等
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# 使用相对导入避免模块问题
import src.email_sender as email_sender_module
import src.ai.ai_analyzer as ai_analyzer_module
import src.utils.database as database_module
from src.utils.logger import get_logger

logger = get_logger('email_test')

def create_test_data():
    """创建测试数据"""
    # 创建测试新闻项
    test_news = [
        database_module.NewsItem(
            id="test1",
            title="央行降准释放流动性，银行股大涨",
            content="央行宣布下调存款准备金率0.5个百分点，向市场释放长期资金约1万亿元。此举旨在保持流动性合理充裕，支持实体经济发展。银行板块应声大涨，工商银行、建设银行等股价纷纷上涨。",
            source="财经日报",
            publish_time=datetime.now(),
            url="https://example.com/news1",
            category="金融",
            keywords=["央行", "降准", "银行股"],
            importance_score=85,
            importance_reasoning="央行政策对金融市场影响重大",
            importance_factors=["政策影响", "市场流动性", "银行收益"],
            impact_degree="高"
        ),
        database_module.NewsItem(
            id="test2", 
            title="新能源汽车销量创新高，产业链公司受益",
            content="1-11月新能源汽车销量同比增长35%，创历史新高。比亚迪、宁德时代等龙头企业业绩亮眼，带动整个产业链上涨。专家预计明年新能源车渗透率将进一步提升。",
            source="汽车周刊",
            publish_time=datetime.now(),
            url="https://example.com/news2",
            category="汽车",
            keywords=["新能源汽车", "销量", "产业链"],
            importance_score=75,
            importance_reasoning="行业增长趋势明确",
            importance_factors=["销量增长", "政策支持", "技术进步"],
            impact_degree="中"
        ),
        database_module.NewsItem(
            id="test3",
            title="某地产公司债务违约，地产股承压",
            content="某知名地产公司宣布无法按期偿还到期债券，引发市场对地产行业流动性的担忧。地产板块今日普遍下跌，投资者情绪谨慎。",
            source="地产观察",
            publish_time=datetime.now(),
            url="https://example.com/news3", 
            category="房地产",
            keywords=["地产", "债务违约", "流动性"],
            importance_score=65,
            importance_reasoning="局部风险事件",
            importance_factors=["债务风险", "行业影响", "投资者情绪"],
            impact_degree="中"
        )
    ]
    
    # 创建测试分析结果
    analysis_results = [
        ai_analyzer_module.AnalysisResult(
            news_id="test1",
            impact_score=18.5,
            summary="央行降准政策利好银行股，预计将提升银行净息差和放贷能力，对金融板块形成重大正面影响。建议关注大型国有银行和股份制银行的投资机会。",
            analysis_time=datetime.now()
        ),
        ai_analyzer_module.AnalysisResult(
            news_id="test2", 
            impact_score=12.3,
            summary="新能源汽车销量持续高增长，产业链景气度高企。重点看好电池、电机、电控等核心零部件企业，以及充电桩运营商的长期价值。",
            analysis_time=datetime.now()
        ),
        ai_analyzer_module.AnalysisResult(
            news_id="test3",
            impact_score=-8.7,
            summary="地产公司债务违约事件可能引发连锁反应，短期内地产股面临调整压力。建议投资者规避高负债率的地产企业，关注基本面稳健的头部房企。",
            analysis_time=datetime.now()
        )
    ]
    
    return test_news, analysis_results

def test_smtp_connection():
    """测试SMTP连接"""
    logger.info("开始测试SMTP连接...")
    
    try:
        email_sender = email_sender_module.EmailSender()
        success = email_sender.test_connection()
        
        if success:
            logger.info("✅ SMTP连接测试成功")
            return True
        else:
            logger.error("❌ SMTP连接测试失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ SMTP连接测试异常: {e}")
        return False

def test_email_template():
    """测试邮件模板生成"""
    logger.info("开始测试邮件模板...")
    
    # 创建测试数据
    test_news, analysis_results = create_test_data()
    
    # 初始化数据库（如果需要）
    db_manager = database_module.DatabaseManager()
    
    # 保存测试新闻到数据库
    for news in test_news:
        try:
            db_manager.save_news_item(news)
            logger.info(f"✅ 保存测试新闻: {news.title}")
        except Exception as e:
            logger.warning(f"⚠️ 保存新闻时出错: {e}")
    
    # 创建邮件发送器
    email_sender = email_sender_module.EmailSender()
    
    # 生成HTML报告
    try:
        html_content = email_sender._generate_html_report(analysis_results)
        
        # 保存HTML到测试结果目录
        test_results_dir = "data/logs"
        os.makedirs(test_results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(test_results_dir, f"test_email_report_{timestamp}.html")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ HTML报告生成成功!")
        logger.info(f"📄 报告已保存到: {output_file}")
        
        # 统计信息
        stats = {
            "total_news": len(analysis_results),
            "positive_impact": sum(1 for r in analysis_results if r.impact_score > 5),
            "negative_impact": sum(1 for r in analysis_results if r.impact_score < -5),
            "neutral_impact": len(analysis_results) - sum(1 for r in analysis_results if abs(r.impact_score) > 5),
            "high_impact": sum(1 for r in analysis_results if abs(r.impact_score) > 10),
            "html_size_bytes": len(html_content.encode('utf-8')),
            "html_size_kb": len(html_content.encode('utf-8')) / 1024
        }
        
        logger.info(f"📊 统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        return True, output_file, stats
        
    except Exception as e:
        logger.error(f"❌ 生成HTML报告失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_mobile_compatibility():
    """测试移动端兼容性特性"""
    logger.info("开始测试移动端兼容性...")
    
    email_sender = email_sender_module.EmailSender()
    test_news, analysis_results = create_test_data()
    
    # 生成HTML
    html_content = email_sender._generate_html_report(analysis_results)
    
    # 检查移动端优化特性
    mobile_features = [
        ("viewport meta标签", "user-scalable=yes"),
        ("响应式字体", "font-size: 13px"),
        ("移动端媒体查询", "@media (max-width: 480px)"),
        ("弹性布局", "display: flex"),
        ("紧凑间距", "padding: 10px"),
        ("小字体大小", "font-size: 11px"),
        ("触摸友好", "border-radius: 6px")
    ]
    
    mobile_check_results = {}
    for feature_name, feature_check in mobile_features:
        found = feature_check in html_content
        mobile_check_results[feature_name] = found
        if found:
            logger.info(f"   ✅ {feature_name}")
        else:
            logger.warning(f"   ❌ {feature_name} (未找到: {feature_check})")
    
    # 内容完整性检查
    content_checks = [
        ("新闻标题", "央行降准释放流动性"),
        ("新闻来源", "财经日报"),
        ("影响评分", "影响: 18.5"),
        ("重要性等级", "重要性: 高"),
        ("AI分析", "AI分析:"),
        ("统计概况", "分析概况"),
        ("免责声明", "投资有风险")
    ]
    
    content_check_results = {}
    for check_name, check_text in content_checks:
        found = check_text in html_content
        content_check_results[check_name] = found
        if found:
            logger.info(f"   ✅ {check_name}")
        else:
            logger.warning(f"   ❌ {check_name} (未找到: {check_text})")
    
    return {
        "mobile_features": mobile_check_results,
        "content_integrity": content_check_results
    }

def test_send_test_email():
    """测试发送测试邮件"""
    logger.info("开始测试发送测试邮件...")
    
    try:
        email_sender = email_sender_module.EmailSender()
        
        # 获取邮件配置
        stats = email_sender.get_stats()
        if not stats.get('smtp_configured'):
            logger.warning("⚠️ SMTP未配置，跳过发送测试")
            return False, "SMTP未配置"
        
        if stats.get('recipients_count', 0) == 0:
            logger.warning("⚠️ 未配置收件人，跳过发送测试")
            return False, "未配置收件人"
        
        # 发送测试邮件
        success = email_sender.send_test_email()
        
        if success:
            logger.info("✅ 测试邮件发送成功")
            return True, "发送成功"
        else:
            logger.error("❌ 测试邮件发送失败")
            return False, "发送失败"
            
    except Exception as e:
        logger.error(f"❌ 发送测试邮件异常: {e}")
        return False, f"异常: {str(e)}"

def test_send_analysis_report():
    """测试发送分析报告邮件"""
    logger.info("开始测试发送分析报告邮件...")
    
    try:
        # 创建测试数据
        test_news, analysis_results = create_test_data()
        
        # 保存测试数据到数据库
        db_manager = database_module.DatabaseManager()
        for news in test_news:
            try:
                db_manager.save_news_item(news)
            except Exception as e:
                logger.warning(f"保存新闻失败: {e}")
        
        # 发送分析报告
        email_sender = email_sender_module.EmailSender()
        
        # 检查配置
        stats = email_sender.get_stats()
        if not stats.get('smtp_configured'):
            logger.warning("⚠️ SMTP未配置，跳过分析报告发送测试")
            return False, "SMTP未配置"
        
        if stats.get('recipients_count', 0) == 0:
            logger.warning("⚠️ 未配置收件人，跳过分析报告发送测试")
            return False, "未配置收件人"
        
        # 发送报告
        success = email_sender.send_analysis_report(
            analysis_results=analysis_results,
            subject="📧 测试 - AI新闻影响分析报告"
        )
        
        if success:
            logger.info("✅ 分析报告邮件发送成功")
            return True, "发送成功"
        else:
            logger.error("❌ 分析报告邮件发送失败")
            return False, "发送失败"
            
    except Exception as e:
        logger.error(f"❌ 发送分析报告邮件异常: {e}")
        return False, f"异常: {str(e)}"

def run_all_email_tests():
    """运行所有邮件相关测试"""
    logger.info("📧 开始运行邮件功能完整测试")
    logger.info("=" * 60)
    
    test_results = {
        "smtp_connection": False,
        "template_generation": False,
        "mobile_compatibility": {},
        "test_email": False,
        "analysis_report": False,
        "overall_success": False
    }
    
    # 1. 测试SMTP连接
    logger.info("\n🔌 1. 测试SMTP连接")
    test_results["smtp_connection"] = test_smtp_connection()
    
    # 2. 测试邮件模板生成
    logger.info("\n📄 2. 测试邮件模板生成")
    template_success, output_file, stats = test_email_template()
    test_results["template_generation"] = template_success
    
    if template_success:
        logger.info(f"模板文件: {output_file}")
        
        # 3. 测试移动端兼容性
        logger.info("\n📱 3. 测试移动端兼容性")
        compatibility_results = test_mobile_compatibility()
        test_results["mobile_compatibility"] = compatibility_results
    
    # 4. 测试发送测试邮件（可选，需要SMTP配置）
    logger.info("\n📤 4. 测试发送测试邮件")
    test_email_success, test_email_msg = test_send_test_email()
    test_results["test_email"] = test_email_success
    logger.info(f"测试邮件结果: {test_email_msg}")
    
    # 5. 测试发送分析报告（可选，需要SMTP配置）
    logger.info("\n📊 5. 测试发送分析报告")
    report_success, report_msg = test_send_analysis_report()
    test_results["analysis_report"] = report_success
    logger.info(f"分析报告结果: {report_msg}")
    
    # 计算测试统计
    core_tests = [
        test_results["template_generation"],
        bool(test_results["mobile_compatibility"].get("mobile_features", {}).get("viewport meta标签", False)),
        bool(test_results["mobile_compatibility"].get("content_integrity", {}).get("新闻标题", False))
    ]
    
    optional_tests = [
        test_results["smtp_connection"],
        test_results["test_email"],
        test_results["analysis_report"]
    ]
    
    # 核心功能统计
    core_success = sum(core_tests)
    core_total = len(core_tests)
    
    # 可选功能统计  
    optional_success = sum(optional_tests)
    optional_total = len(optional_tests)
    
    # 总体统计
    total_success = core_success + optional_success
    total_tests = core_total + optional_total
    
    test_results["overall_success"] = core_success >= 2  # 至少2个核心功能要通过
    
    # 生成测试报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"data/logs/email_test_results_{timestamp}.json"
    os.makedirs("data/logs", exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)
    
    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("📋 邮件测试总结")
    logger.info("=" * 60)
    logger.info(f"✅ 核心功能: {core_success}/{core_total} 通过")
    logger.info(f"📧 可选功能: {optional_success}/{optional_total} 通过") 
    logger.info(f"📄 详细结果已保存到: {report_file}")
    
    if template_success:
        logger.info(f"🌐 HTML模板文件: {output_file}")
        logger.info("💡 请在浏览器中打开HTML文件查看效果")
        logger.info("📱 建议在手机浏览器中测试移动端效果")
    
    if test_results["overall_success"]:
        logger.info("🎉 邮件功能测试整体通过!")
    else:
        logger.warning("⚠️ 邮件功能测试存在问题，请检查日志")
    
    # 返回统计格式，与其他测试模块一致
    return {
        "total": total_tests,
        "success": total_success,
        "failed": total_tests - total_success,
        "core_success": core_success,
        "core_total": core_total,
        "optional_success": optional_success,
        "optional_total": optional_total,
        "success_rate": (total_success / total_tests * 100) if total_tests > 0 else 0,
        "template_file": output_file if template_success else None,
        "detailed_results": test_results
    }

if __name__ == "__main__":
    run_all_email_tests() 