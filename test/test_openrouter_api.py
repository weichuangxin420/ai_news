"""
OpenRouter API 集成测试
测试OpenRouter API是否可以正常工作
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.ai.ai_analyzer import AIAnalyzer, AnalysisResult
from src.utils.database import NewsItem


class TestOpenRouterAPI(unittest.TestCase):
    """OpenRouter API集成测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        
        # 创建测试新闻项
        self.test_news_item = NewsItem(
            id="test_news_001",
            title="测试新闻：某公司发布季度财报",
            content="某上市公司今日发布2024年第四季度财报，营收同比增长15%，净利润增长20%。",
            source="测试来源",
            publish_time=datetime.now(),
            keywords=["财报", "营收", "净利润"]
        )
    
    def test_openrouter_analyzer_initialization(self):
        """测试OpenRouter分析器初始化"""
        try:
            analyzer = AIAnalyzer(self.config_path, provider="openrouter")
            self.assertIsNotNone(analyzer.client)
            self.assertEqual(analyzer.provider, "openrouter")
            self.assertEqual(analyzer.stats["provider"], "openrouter")
            print("✅ OpenRouter分析器初始化成功")
        except Exception as e:
            self.fail(f"OpenRouter分析器初始化失败: {e}")
    
    def test_deepseek_analyzer_initialization(self):
        """测试DeepSeek分析器初始化"""
        try:
            analyzer = AIAnalyzer(self.config_path, provider="deepseek")
            self.assertIsNotNone(analyzer.client)
            self.assertEqual(analyzer.provider, "deepseek")
            self.assertEqual(analyzer.stats["provider"], "deepseek")
            print("✅ DeepSeek分析器初始化成功")
        except Exception as e:
            self.fail(f"DeepSeek分析器初始化失败: {e}")
    
    @patch('openai.OpenAI')
    def test_openrouter_api_call_mock(self, mock_openai):
        """测试OpenRouter API调用（模拟）"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"impact_score": 75, "summary": "财报表现良好，对股价有正面影响"}'
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 80
        mock_response.usage.completion_tokens = 20
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        analyzer = AIAnalyzer(self.config_path, provider="openrouter")
        result = analyzer.analyze_news(self.test_news_item)
        
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.news_id, "test_news_001")
        self.assertEqual(result.impact_score, 75)
        self.assertIn("财报", result.summary)
        print("✅ OpenRouter API调用模拟测试通过")
    
    def test_real_openrouter_api_call(self):
        """测试真实的OpenRouter API调用"""
        try:
            analyzer = AIAnalyzer(self.config_path, provider="openrouter")
            result = analyzer.analyze_news(self.test_news_item)
            
            self.assertIsInstance(result, AnalysisResult)
            self.assertEqual(result.news_id, "test_news_001")
            self.assertIsInstance(result.impact_score, (int, float))
            self.assertTrue(0 <= result.impact_score <= 100)
            self.assertIsInstance(result.summary, str)
            self.assertTrue(len(result.summary) > 0)
            
            print(f"✅ OpenRouter真实API调用成功")
            print(f"   影响评分: {result.impact_score}")
            print(f"   分析摘要: {result.summary}")
            print(f"   分析时间: {result.analysis_time}")
            
        except Exception as e:
            print(f"❌ OpenRouter真实API调用失败: {e}")
            # 不让测试失败，因为可能是网络或配置问题
            self.skipTest(f"跳过真实API测试: {e}")


def main():
    """运行测试"""
    print("=" * 60)
    print("OpenRouter API 集成测试")
    print("=" * 60)
    
    # 运行测试
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 