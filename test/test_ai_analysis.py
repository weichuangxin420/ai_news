#!/usr/bin/env python3
"""
AI分析功能测试模块
测试AI分析器的核心功能（只保留主流程使用的逻辑）
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
    """AI分析测试器 - 只测试主流程使用的核心功能"""
    
    def __init__(self):
        """初始化测试器"""
        self.analyzer = None
        self.results = {}
        
    def test_analyzer_initialization(self) -> bool:
        """测试分析器初始化"""
        print("🔍 测试AI分析器初始化...")
        
        try:
            # 测试标准分析器
            self.analyzer = AIAnalyzer()
            print("✅ AI分析器初始化成功")
                
            self.results["initialization"] = {
                "status": "success",
                "analyzer_available": True
            }
            return True
            
        except Exception as e:
            print(f"❌ AI分析器初始化失败: {e}")
            self.results["initialization"] = {"status": "failed", "error": str(e)}
            return False

    def test_single_news_analysis(self) -> Dict[str, any]:
        """测试单条新闻分析（基础功能）"""
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
            result = self.analyzer.analyze_news(test_news)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            print(f"✅ 单条新闻分析完成")
            print(f"   分析时间: {analysis_time:.2f}秒")
            print(f"   影响评分: {result.impact_score}/100")
            print(f"   分析摘要: {result.summary[:50]}...")
            
            self.results["single_analysis"] = {
                "status": "success",
                "analysis_time": analysis_time,
                "impact_score": result.impact_score,
                "summary": result.summary
            }
            return self.results["single_analysis"]
            
        except Exception as e:
            print(f"❌ 单条新闻分析失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["single_analysis"] = result
            return result



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
        """运行所有核心测试"""
        print("🧪 AI分析核心功能测试")
        print("=" * 80)
        
        # 1. 测试初始化
        self.test_analyzer_initialization()
        
        # 2. 测试单条分析（基础功能）
        self.test_single_news_analysis()
        
        # 显示测试总结
        self.print_summary()
        
        return self.results

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📋 AI分析核心测试总结")
        print("-" * 80)
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results.values() if r.get("status") == "success"])
        
        print(f"总测试数: {total_tests}")
        print(f"成功数: {successful_tests}")
        print(f"失败数: {total_tests - successful_tests}")
        print(f"成功率: {successful_tests/max(total_tests,1)*100:.1f}%")
        
        # 显示各项测试结果
        for test_name, result in self.results.items():
            status_icon = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_icon} {test_name}")


def run_ai_analysis_tests():
    """运行AI分析测试的主函数"""
    tester = AIAnalysisTester()
    results = tester.run_all_tests()
    return results


if __name__ == "__main__":
    run_ai_analysis_tests() 