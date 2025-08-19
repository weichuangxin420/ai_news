#!/usr/bin/env python3
"""
新闻收集功能测试模块
测试新闻收集器的各项功能
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.news_collector import NewsCollector
from src.utils.database import NewsItem, db_manager
from src.utils.logger import get_logger

logger = get_logger("test_news_collection")


class NewsCollectionTester:
    """新闻收集测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.collector = None
        self.results = {}
        
    def test_collector_initialization(self) -> bool:
        """测试收集器初始化"""
        print("🔍 测试新闻收集器初始化...")
        
        try:
            self.collector = NewsCollector()
            print("✅ 新闻收集器初始化成功")
            
            # 检查配置加载
            if self.collector.config:
                print(f"   配置加载成功，包含 {len(self.collector.config)} 个配置项")
            else:
                print("⚠️  配置为空或加载失败")
                
            self.results["initialization"] = {"status": "success"}
            return True
            
        except Exception as e:
            print(f"❌ 新闻收集器初始化失败: {e}")
            self.results["initialization"] = {"status": "failed", "error": str(e)}
            return False

    def test_news_collection(self) -> Dict[str, any]:
        """测试新闻收集功能"""
        print("\n📰 测试新闻收集功能")
        print("-" * 60)
        
        if not self.collector:
            print("❌ 收集器未初始化")
            return {"status": "failed", "error": "collector_not_initialized"}
            
        try:
            print("🔍 开始收集新闻...")
            start_time = time.time()
            
            news_list = self.collector.collect_all_news()
            
            end_time = time.time()
            collection_time = end_time - start_time
            
            print(f"✅ 新闻收集完成")
            print(f"   收集数量: {len(news_list)}")
            print(f"   用时: {collection_time:.2f}秒")
            
            # 获取统计信息
            stats = self.collector.get_stats()
            print(f"   统计信息: {stats}")
            
            # 显示部分新闻示例
            if news_list:
                print(f"\n📋 新闻示例（前3条）:")
                for i, news in enumerate(news_list[:3]):
                    print(f"   {i+1}. [{news.source}] {news.title[:50]}...")
                    print(f"      分类: {news.category}, 关键词: {news.keywords[:3]}")
            
            result = {
                "status": "success",
                "news_count": len(news_list),
                "collection_time": collection_time,
                "stats": stats,
                "sample_news": [
                    {
                        "title": news.title[:100],
                        "source": news.source,
                        "category": news.category
                    } for news in news_list[:3]
                ]
            }
            
            self.results["collection"] = result
            return result
            
        except Exception as e:
            print(f"❌ 新闻收集失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["collection"] = result
            return result

    def test_data_processing(self) -> Dict[str, any]:
        """测试数据处理功能"""
        print("\n🔄 测试数据处理功能")
        print("-" * 60)
        
        try:
            # 创建测试新闻数据
            test_news = self._create_test_news()
            print(f"🔍 创建了 {len(test_news)} 条测试新闻")
            
            # 测试去重功能
            print("🔍 测试新闻去重功能...")
            
            # 添加重复新闻
            duplicate_news = test_news + test_news[:2]  # 添加2条重复新闻
            
            filtered_news = self.collector._deduplicate_news(duplicate_news)
            
            print(f"   原始数量: {len(duplicate_news)}")
            print(f"   去重后数量: {len(filtered_news)}")
            print(f"   去重数量: {len(duplicate_news) - len(filtered_news)}")
            
            # 测试标签生成
            print("🔍 测试标签生成功能...")
            if test_news:
                sample_news = test_news[0]
                tags = self.collector._generate_simple_tags(sample_news.title, sample_news.content)
                print(f"   示例标签: {tags}")
            
            result = {
                "status": "success",
                "original_count": len(duplicate_news),
                "filtered_count": len(filtered_news),
                "deduplication_count": len(duplicate_news) - len(filtered_news),
                "sample_tags": tags if test_news else []
            }
            
            self.results["data_processing"] = result
            return result
            
        except Exception as e:
            print(f"❌ 数据处理测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["data_processing"] = result
            return result

    def test_database_integration(self) -> Dict[str, any]:
        """测试数据库集成"""
        print("\n💾 测试数据库集成")
        print("-" * 60)
        
        try:
            # 测试数据库连接
            print("🔍 测试数据库连接...")
            # 数据库在导入时已经初始化，这里只需要测试基本操作
            stats = db_manager.get_stats()
            print("✅ 数据库连接正常")
            
            # 获取数据库中的新闻数量
            from datetime import datetime, timedelta
            start_time = datetime.now() - timedelta(hours=24)
            recent_news = db_manager.get_news_items(limit=10, start_time=start_time)
            print(f"   最近24小时新闻: {len(recent_news)}条")
            
            # 获取统计信息
            stats = db_manager.get_stats()
            print(f"   数据库统计: {stats}")
            
            result = {
                "status": "success",
                "recent_news_count": len(recent_news),
                "database_stats": stats
            }
            
            self.results["database"] = result
            return result
            
        except Exception as e:
            print(f"❌ 数据库集成测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["database"] = result
            return result

    def _create_test_news(self) -> List[NewsItem]:
        """创建测试新闻数据"""
        test_news = []
        
        test_data = [
            {
                "title": "A股市场今日大涨，科技股领涨",
                "content": "今日A股市场表现强劲，上证指数涨2.5%，深证成指涨3.2%，科技股成为领涨板块。",
                "source": "测试源1",
                "category": "股市"
            },
            {
                "title": "央行宣布降准0.5个百分点",
                "content": "中国人民银行今日宣布下调存款准备金率0.5个百分点，释放流动性约8000亿元。",
                "source": "测试源2", 
                "category": "货币政策"
            },
            {
                "title": "新能源汽车销量创新高",
                "content": "11月新能源汽车销量达到80万辆，同比增长35%，市场渗透率突破30%。",
                "source": "测试源3",
                "category": "汽车"
            }
        ]
        
        for i, data in enumerate(test_data):
            news = NewsItem()
            news.title = data["title"]
            news.content = data["content"]
            news.source = data["source"]
            news.category = data["category"]
            news.url = f"https://example.com/news/{i+1}"
            news.publish_time = datetime.now()
            news.keywords = ["测试", "财经"]
            test_news.append(news)
            
        return test_news

    def run_all_tests(self) -> Dict[str, dict]:
        """运行所有测试"""
        print("🧪 新闻收集功能测试")
        print("=" * 80)
        
        # 1. 测试初始化
        self.test_collector_initialization()
        
        # 2. 测试数据库集成
        self.test_database_integration()
        
        # 3. 测试数据处理
        self.test_data_processing()
        
        # 4. 测试新闻收集
        self.test_news_collection()
        
        # 显示测试总结
        self.print_summary()
        
        return self.results

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📋 新闻收集测试总结")
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
            
            if result.get("status") == "success":
                if test_name == "collection":
                    print(f"   收集到 {result.get('news_count', 0)} 条新闻")
                elif test_name == "database":
                    print(f"   数据库中有 {result.get('recent_news_count', 0)} 条最近新闻")


def run_news_collection_tests():
    """运行新闻收集测试的主函数"""
    tester = NewsCollectionTester()
    results = tester.run_all_tests()
    return results


if __name__ == "__main__":
    run_news_collection_tests() 