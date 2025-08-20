#!/usr/bin/env python3
"""
AI分析功能测试模块
测试AI分析器的各项功能
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai.ai_analyzer import AIAnalyzer
from src.utils.database import NewsItem, db_manager
from src.utils.logger import get_logger

logger = get_logger("test_ai_analysis")


class AIAnalysisTester:
    """AI分析测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.analyzer = None
        self.results = {}
        self.mock_mode = False
        
    def test_analyzer_initialization(self) -> bool:
        """测试分析器初始化"""
        print("🔍 测试AI分析器初始化...")
        
        try:
            self.analyzer = AIAnalyzer()
            print("✅ AI分析器初始化成功")
            
            # 检查API配置
            api_key = self.analyzer.config.get("ai_analysis", {}).get("deepseek", {}).get("api_key", "")
            if not api_key or api_key == "YOUR_DEEPSEEK_API_KEY":
                print("⚠️  未配置DeepSeek API密钥，将使用模拟分析模式")
                self.mock_mode = True
            else:
                print("🔑 已配置DeepSeek API密钥，将使用真实分析模式")
                self.mock_mode = False
                
            self.results["initialization"] = {
                "status": "success",
                "mock_mode": self.mock_mode
            }
            return True
            
        except Exception as e:
            print(f"❌ AI分析器初始化失败: {e}")
            self.results["initialization"] = {"status": "failed", "error": str(e)}
            return False

    def test_single_news_analysis(self) -> Dict[str, any]:
        """测试单条新闻分析"""
        print("\n🤖 测试单条新闻分析")
        print("-" * 60)
        
        if not self.analyzer:
            print("❌ 分析器未初始化")
            return {"status": "failed", "error": "analyzer_not_initialized"}
            
        try:
            # 创建测试新闻
            test_news = self._create_test_news()[0]  # 取第一条
            print(f"🔍 分析测试新闻: {test_news.title[:50]}...")
            
            start_time = time.time()
            result = self.analyzer.analyze_single_news(test_news)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            print(f"✅ 单条新闻分析完成")
            print(f"   分析时间: {analysis_time:.2f}秒")
            print(f"   影响评分: {result.impact_score}/100")
            print(f"   分析摘要: {result.summary[:50]}...")
            print(f"   分析模式: {'真实' if not self.mock_mode else '模拟'}")
            
            self.results["single_analysis"] = {
                "status": "success",
                "analysis_time": analysis_time,
                "impact_score": result.impact_score,
                "summary": result.summary,
                "mode": "real" if not self.mock_mode else "mock"
            }
            return self.results["single_analysis"]
            
        except Exception as e:
            print(f"❌ 单条新闻分析失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["single_analysis"] = result
            return result

    def test_batch_analysis(self, batch_size: int = 3) -> Dict[str, any]:
        """测试批量新闻分析"""
        print(f"\n📊 测试批量新闻分析（{batch_size}条）")
        print("-" * 60)
        
        if not self.analyzer:
            print("❌ 分析器未初始化")
            return {"status": "failed", "error": "analyzer_not_initialized"}
            
        try:
            # 获取测试新闻
            test_news_list = self._get_test_news_for_analysis(batch_size)
            
            if not test_news_list:
                print("❌ 没有可分析的新闻")
                return {"status": "failed", "error": "no_news_available"}
            
            print(f"🔍 开始批量分析 {len(test_news_list)} 条新闻...")
            
            start_time = time.time()
            results = self.analyzer.batch_analyze(test_news_list)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            print(f"✅ 批量分析完成")
            print(f"   分析数量: {len(results)}")
            print(f"   总用时: {analysis_time:.2f}秒")
            print(f"   平均用时: {analysis_time/max(len(results),1):.2f}秒/条")
            print(f"   分析模式: {'模拟' if self.mock_mode else '真实'}")
            
            # 显示分析结果示例
            if results:
                print(f"\n📋 分析结果示例:")
                for i, result in enumerate(results[:3], 1):
                    print(f"   {i}. 影响评分: {result.impact_score}/100")
                    print(f"      摘要: {result.summary[:50]}...")
                    if i < 3:
                        print()
            
            test_result = {
                "status": "success",
                "analyzed_count": len(results),
                "total_time": analysis_time,
                "average_time": analysis_time/max(len(results),1),
                "mock_mode": self.mock_mode,
                "sample_results": [
                    {
                        "impact_score": result.impact_score,
                        "summary": result.summary[:50]
                    } for result in results[:2]
                ]
            }
            
            self.results["batch_analysis"] = test_result
            return test_result
            
        except Exception as e:
            print(f"❌ 批量分析失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["batch_analysis"] = result
            return result

    def test_analysis_quality(self) -> Dict:
        """测试分析质量"""
        print("🎯 测试分析质量")
        print("------------------------------------------------------------")
        
        try:
            print("🔍 测试分析质量...")
            
            # 定义测试用例
            test_cases = [
                {
                    "news": NewsItem(
                        id="quality_test_1",
                        title="银行股大涨，建设银行涨停，工商银行涨8%",
                        content="今日银行板块大幅上涨，建设银行强势涨停，工商银行涨幅达8%，银行业绩超预期。",
                        source="测试",
                        category="银行",
                        keywords=["银行", "大涨", "涨停"]
                    ),
                    "expected_range": (60, 100)  # 预期高影响评分
                },
                {
                    "news": NewsItem(
                        id="quality_test_2", 
                        title="科技股暴跌，腾讯跌5%，阿里巴巴跌7%",
                        content="科技股今日遭遇重挫，腾讯控股跌5%，阿里巴巴跌7%，投资者担忧监管政策。",
                        source="测试",
                        category="科技", 
                        keywords=["科技", "暴跌", "下跌"]
                    ),
                    "expected_range": (0, 40)  # 预期低影响评分
                }
            ]
            
            score_correct = 0
            total_tests = len(test_cases)
            
            for test_case in test_cases:
                news = test_case["news"]
                expected_min, expected_max = test_case["expected_range"]
                
                result = self.analyzer.analyze_single_news(news)
                
                print(f"   新闻: {news.title[:30]}...")
                print(f"   预期评分范围: {expected_min}-{expected_max}")
                print(f"   实际评分: {result.impact_score}")
                print()
                
                # 检查评分是否在合理范围内
                if expected_min <= result.impact_score <= expected_max:
                    score_correct += 1
            
            score_accuracy = score_correct / total_tests * 100
            overall_quality = score_accuracy
            
            print(f"📊 分析质量评估:")
            print(f"   评分准确性: {score_accuracy:.1f}%")
            print(f"   综合质量评分: {overall_quality:.1f}%")
            
            self.results["analysis_quality"] = {
                "status": "success",
                "score_accuracy": score_accuracy,
                "overall_quality": overall_quality,
                "total_tests": total_tests
            }
            
            return self.results["analysis_quality"]
            
        except Exception as e:
            print(f"❌ 分析质量测试失败: {e}")
            self.results["analysis_quality"] = {
                "status": "error",
                "error": str(e)
            }
            return self.results["analysis_quality"]

    def _get_test_news_for_analysis(self, limit: int) -> List[NewsItem]:
        """获取用于分析的测试新闻"""
        # 首先尝试从数据库获取
        from datetime import datetime, timedelta
        start_time = datetime.now() - timedelta(hours=24)
        recent_news = db_manager.get_news_items(limit=limit, start_time=start_time)
        
        if recent_news:
            print(f"   从数据库获取 {len(recent_news)} 条最近新闻")
            return recent_news
        else:
            print(f"   数据库中没有新闻，创建 {limit} 条测试新闻")
            return self._create_test_news()[:limit]

    def _create_test_news(self) -> List[NewsItem]:
        """创建测试新闻数据"""
        test_news = []
        
        test_data = [
            {
                "title": "A股三大指数集体上涨，沪指涨2.3%创新高",
                "content": "今日A股市场表现强劲，上证指数涨2.3%，深证成指涨2.8%，创业板指涨3.1%。券商、银行板块领涨。",
                "category": "股市行情"
            },
            {
                "title": "央行降准释放流动性，银行股应声上涨",
                "content": "央行宣布下调存款准备金率0.25个百分点，释放长期资金约5000亿元，银行股集体上涨。",
                "category": "货币政策"
            },
            {
                "title": "新能源汽车产业政策利好，相关概念股大涨",
                "content": "国家发布新能源汽车产业发展政策，比亚迪、特斯拉概念股大涨，板块涨幅超过5%。",
                "category": "新能源"
            },
            {
                "title": "科技股遭遇重挫，芯片板块跌幅居前",
                "content": "受国际形势影响，科技股今日大幅下跌，芯片板块跌幅居前，中芯国际跌超8%。",
                "category": "科技"
            }
        ]
        
        for i, data in enumerate(test_data):
            news = NewsItem()
            news.title = data["title"]
            news.content = data["content"]
            news.source = "测试数据源"
            news.category = data["category"]
            news.url = f"https://example.com/test/{i+1}"
            news.publish_time = datetime.now()
            news.keywords = ["A股", "财经"]
            test_news.append(news)
            
        return test_news

    def run_all_tests(self) -> Dict[str, dict]:
        """运行所有测试"""
        print("🧪 AI分析功能测试")
        print("=" * 80)
        
        # 1. 测试初始化
        self.test_analyzer_initialization()
        
        # 2. 测试单条分析
        self.test_single_news_analysis()
        
        # 3. 测试批量分析
        self.test_batch_analysis()
        
        # 4. 测试分析质量
        self.test_analysis_quality()
        
        # 显示测试总结
        self.print_summary()
        
        return self.results

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📋 AI分析测试总结")
        print("-" * 80)
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results.values() if r.get("status") == "success"])
        
        print(f"总测试数: {total_tests}")
        print(f"成功数: {successful_tests}")
        print(f"失败数: {total_tests - successful_tests}")
        print(f"成功率: {successful_tests/max(total_tests,1)*100:.1f}%")
        print(f"分析模式: {'模拟' if self.mock_mode else '真实'}")
        
        # 显示各项测试结果
        for test_name, result in self.results.items():
            status_icon = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_icon} {test_name}")
            
            if result.get("status") == "success":
                if test_name == "batch_analysis":
                    count = result.get("analyzed_count", 0)
                    avg_time = result.get("average_time", 0)
                    print(f"   分析了 {count} 条新闻，平均 {avg_time:.2f}秒/条")
                elif test_name == "analysis_quality":
                    score = result.get("quality_score", {}).get("overall_score", 0)
                    print(f"   分析质量评分: {score:.1f}%")


def run_ai_analysis_tests():
    """运行AI分析测试的主函数"""
    tester = AIAnalysisTester()
    results = tester.run_all_tests()
    return results


if __name__ == "__main__":
    run_ai_analysis_tests() 