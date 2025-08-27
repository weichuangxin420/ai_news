#!/usr/bin/env python3
"""
深度分析功能测试模块
测试针对高重要性新闻的深度分析功能
"""

import unittest
import time
from datetime import datetime
from unittest.mock import patch
import sys
import os
import yaml

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.ai.deep_analyzer import DeepAnalyzer, DeepAnalysisResult
from src.utils.database import NewsItem
from src.utils.logger import get_logger

logger = get_logger("test_deep_analysis")


class TestDeepAnalyzer(unittest.TestCase):
    """深度分析器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 加载真实配置文件
        import yaml
        config_path = os.path.join(project_root, "config/config.yaml")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.test_config = yaml.safe_load(f) or {}
            logger.info("✅ 已加载真实配置文件进行API测试")
        except Exception as e:
            logger.warning(f"⚠️  无法加载配置文件，使用测试配置: {e}")
            # 备用测试配置
            self.test_config = {
                "ai_analysis": {
                    "openrouter": {
                        "api_key": "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",
                        "base_url": "https://openrouter.ai/api/v1",
                        "model": "deepseek/deepseek-r1-0528:free",
                        "max_tokens": 2000,
                        "temperature": 0.1
                    },
                    "deep_analysis": {
                        "enabled": True,
                        "score_threshold": 70,
                        "max_concurrent": 3,
                        "search_timeout": 30,
                        "max_search_keywords": 5,
                        "report_max_length": 200,
                        "enable_score_adjustment": True,
                        "search_retry_count": 2
                    }
                }
            }
        
        # 创建测试新闻项
        self.high_importance_news = NewsItem(
            id="test_high_001",
            title="央行宣布降准0.5个百分点，释放流动性约1万亿元",
            content="中国人民银行决定于2024年12月15日下调金融机构存款准备金率0.5个百分点，此次降准将释放长期资金约1万亿元。",
            source="央行官网",
            category="货币政策",
            importance_score=85
        )
        
        self.low_importance_news = NewsItem(
            id="test_low_001",
            title="某公司发布三季度财报",
            content="某上市公司发布三季度财报，营收同比增长5%。",
            source="财经网",
            category="公司新闻",
            importance_score=45
        )
        
    def test_deep_analyzer_initialization(self):
        """测试深度分析器初始化"""
        logger.info("\n🔧 测试深度分析器初始化...")
        
        try:
            analyzer = DeepAnalyzer(config=self.test_config)
            
            # 验证配置加载
            self.assertTrue(analyzer.enabled)
            self.assertEqual(analyzer.score_threshold, 70)
            self.assertEqual(analyzer.max_concurrent, 3)
            
            logger.info("✅ 深度分析器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 深度分析器初始化失败: {e}")
            return False
    
    def test_should_analyze_logic(self):
        """测试深度分析判断逻辑"""
        logger.info("\n🧠 测试深度分析判断逻辑...")
        
        try:
            analyzer = DeepAnalyzer(config=self.test_config)
            
            # 测试高重要性新闻（应该分析）
            should_analyze_high = analyzer.should_analyze(self.high_importance_news)
            self.assertTrue(should_analyze_high)
            logger.info(f"✅ 高重要性新闻({self.high_importance_news.importance_score}分)需要深度分析")
            
            # 测试低重要性新闻（不应该分析）
            should_analyze_low = analyzer.should_analyze(self.low_importance_news)
            self.assertFalse(should_analyze_low)
            logger.info(f"✅ 低重要性新闻({self.low_importance_news.importance_score}分)不需要深度分析")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 深度分析判断逻辑测试失败: {e}")
            return False
    
    @patch('src.ai.deep_analyzer.baidu_search_tool')
    def test_search_functionality(self, mock_search):
        """测试百度搜索功能"""
        logger.info("\n🔎 测试百度搜索功能...")
        
        try:
            # 模拟搜索成功的返回结果
            mock_search.return_value = """搜索结果摘要：
关键词：央行 降准
搜索状态：成功
内容长度：15000字符

搜索总结：成功从百度获取到关于'央行 降准'的搜索结果页面，页面包含大量相关信息。"""
            
            analyzer = DeepAnalyzer(config=self.test_config)
            
            # 测试搜索功能
            keywords = ["央行", "降准"]
            search_results, search_success = analyzer._perform_search(keywords, self.high_importance_news.title)
            
            self.assertTrue(search_success)
            self.assertIn("搜索状态：成功", search_results)
            
            # 验证搜索工具被正确调用
            mock_search.assert_called_once()
            
            logger.info("✅ 百度搜索功能测试成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 百度搜索功能测试失败: {e}")
            return False
    
    def test_single_news_deep_analysis(self):
        """测试单条新闻深度分析"""
        logger.info("\n🔬 测试单条新闻深度分析...")
        
        try:
            # 使用真实配置进行API调用测试
            analyzer = DeepAnalyzer(config=self.test_config)
            
            # 执行真实的深度分析
            result = analyzer.analyze_news_deep(self.high_importance_news)
            
            # 验证结果
            self.assertIsInstance(result, DeepAnalysisResult)
            self.assertEqual(result.news_id, self.high_importance_news.id)
            self.assertEqual(result.original_score, self.high_importance_news.importance_score)
            self.assertIsInstance(result.search_keywords, list)
            self.assertIsInstance(result.deep_analysis_report, str)
            self.assertIsInstance(result.adjusted_score, int)
            self.assertGreater(len(result.deep_analysis_report), 30)  # 确保有实际内容
            
            logger.info("✅ 单条新闻深度分析成功")
            logger.info(f"   原始分数: {result.original_score} -> 调整分数: {result.adjusted_score}")
            logger.info(f"   搜索关键词: {result.search_keywords}")
            logger.info(f"   搜索成功: {result.search_success}")
            logger.info(f"   分析报告: {result.deep_analysis_report[:100]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 单条新闻深度分析测试失败: {e}")
            return False
    
    def test_batch_deep_analysis(self):
        """测试批量深度分析"""
        logger.info("\n📚 测试批量深度分析...")
        
        try:
            # 创建测试新闻列表
            news_list = [
                self.high_importance_news,
                self.low_importance_news,
                NewsItem(
                    id="test_high_002",
                    title="重要监管政策发布，对银行业产生重大影响",
                    content="金融监管部门发布重要政策，要求银行业加强风险管控，提高资本充足率",
                    source="监管部门",
                    importance_score=75
                )
            ]
            
            # 使用真实配置进行API调用测试
            analyzer = DeepAnalyzer(config=self.test_config)
            
            # 执行真实的批量深度分析
            results = analyzer.batch_analyze_deep(news_list)
            
            # 验证结果
            self.assertIsInstance(results, list)
            
            # 应该只分析重要性分数>=70的新闻
            expected_count = sum(1 for news in news_list if news.importance_score >= 70)
            self.assertEqual(len(results), expected_count)
            
            # 验证每个结果的质量
            for result in results:
                self.assertIsInstance(result, DeepAnalysisResult)
                self.assertGreaterEqual(result.original_score, 70)
                self.assertGreater(len(result.deep_analysis_report), 30)
            
            logger.info("✅ 批量深度分析成功")
            logger.info(f"   输入新闻数: {len(news_list)}")
            logger.info(f"   分析结果数: {len(results)}")
            logger.info(f"   高重要性新闻: {expected_count}")
            
            # 显示分析结果详情
            for i, result in enumerate(results):
                logger.info(f"   新闻{i+1}: {result.original_score}→{result.adjusted_score}分, 搜索成功: {result.search_success}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 批量深度分析测试失败: {e}")
            return False


def run_deep_analysis_tests():
    """运行深度分析测试"""
    logger.info("🧪 运行深度分析功能测试")
    logger.info("=" * 60)
    
    # 创建测试实例并初始化
    test_instance = TestDeepAnalyzer()
    test_instance.setUp()
    
    tests = [
        ("深度分析器初始化", test_instance.test_deep_analyzer_initialization),
        ("深度分析判断逻辑", test_instance.test_should_analyze_logic),
        ("百度搜索功能", test_instance.test_search_functionality),
        ("单条新闻深度分析", test_instance.test_single_news_deep_analysis),
        ("批量深度分析", test_instance.test_batch_deep_analysis),
    ]
    
    results = {}
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n📋 {test_name}")
            success = test_func()
            results[test_name] = {"status": "success" if success else "failed"}
            if success:
                passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} 执行异常: {e}")
            results[test_name] = {"status": "error", "error": str(e)}
    
    # 显示汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 深度分析测试汇总")
    logger.info("=" * 60)
    logger.info(f"总测试数: {total}")
    logger.info(f"通过测试: {passed}")
    logger.info(f"失败测试: {total - passed}")
    logger.info(f"成功率: {passed/total*100:.1f}%")
    
    # 显示详细结果
    logger.info(f"\n📋 详细结果:")
    for test_name, result in results.items():
        status_icon = "✅" if result["status"] == "success" else "❌"
        logger.info(f"{status_icon} {test_name}")
        if result["status"] == "error":
            logger.error(f"     错误: {result['error']}")
    
    return {
        "total": total,
        "success": passed,
        "failed": total - passed,
        "results": results
    }


if __name__ == "__main__":
    run_deep_analysis_tests() 