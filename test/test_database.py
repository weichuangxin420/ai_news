#!/usr/bin/env python3
"""
数据库功能测试模块
测试数据库的各项操作功能
"""

import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.database import db_manager, NewsItem
from src.ai_analyzer import AnalysisResult
from src.utils.logger import get_logger

logger = get_logger("test_database")


class DatabaseTester:
    """数据库测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.results = {}
        self.test_db_path = None
        self.original_db_path = None
        
    def setup_test_database(self):
        """设置测试数据库"""
        print("🔧 设置测试数据库...")
        
        # 创建临时数据库文件
        temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(temp_dir, "test_ai_news.db")
        
        # 备份原始数据库路径
        self.original_db_path = db_manager.db_path
        
        # 设置为测试数据库
        db_manager.db_path = self.test_db_path
        
        print(f"   测试数据库路径: {self.test_db_path}")

    def cleanup_test_database(self):
        """清理测试数据库"""
        if self.test_db_path and os.path.exists(self.test_db_path):
            # 恢复原始数据库路径
            db_manager.db_path = self.original_db_path
            
            # 删除测试数据库文件夹
            test_dir = os.path.dirname(self.test_db_path)
            shutil.rmtree(test_dir, ignore_errors=True)
            print("🧹 清理测试数据库完成")

    def test_database_initialization(self) -> Dict[str, any]:
        """测试数据库初始化"""
        print("\n🔍 测试数据库初始化")
        print("-" * 60)
        
        try:
            # 数据库在导入时已经初始化，这里测试连接
            stats = db_manager.get_stats()
            
            # 检查数据库文件是否创建
            if os.path.exists(self.test_db_path):
                print("✅ 数据库文件创建成功")
                file_size = os.path.getsize(self.test_db_path)
                print(f"   数据库文件大小: {file_size} 字节")
            else:
                print("❌ 数据库文件创建失败")
                return {"status": "failed", "error": "database_file_not_created"}
            
            # 测试连接
            stats = db_manager.get_stats()
            print(f"✅ 数据库连接正常")
            print(f"   初始统计: {stats}")
            
            result = {
                "status": "success",
                "file_size": file_size,
                "initial_stats": stats
            }
            
            self.results["initialization"] = result
            return result
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["initialization"] = result
            return result

    def test_news_operations(self) -> Dict[str, any]:
        """测试新闻数据操作"""
        print("\n📰 测试新闻数据操作")
        print("-" * 60)
        
        try:
            # 创建测试新闻
            test_news = self._create_test_news_items()
            print(f"🔍 创建了 {len(test_news)} 条测试新闻")
            
            # 测试批量保存
            print("🔍 测试批量保存新闻...")
            saved_count = db_manager.save_news_items_batch(test_news)
            print(f"   保存成功: {saved_count} 条")
            
            if saved_count != len(test_news):
                print(f"⚠️  期望保存 {len(test_news)} 条，实际保存 {saved_count} 条")
            
            # 测试查询新闻
            print("🔍 测试查询新闻...")
            retrieved_news = db_manager.get_news_items(limit=10)
            print(f"   查询到: {len(retrieved_news)} 条新闻")
            
            # 测试去重检查
            print("🔍 测试去重检查...")
            first_news = test_news[0]
            exists = db_manager.check_news_exists(first_news.title, first_news.url)
            print(f"   去重检查: {'存在' if exists else '不存在'}")
            
            # 测试最近新闻查询
            print("🔍 测试最近新闻查询...")
            from datetime import datetime, timedelta
            start_time = datetime.now() - timedelta(hours=1)
            recent_news = db_manager.get_news_items(limit=5, start_time=start_time)
            print(f"   最近1小时新闻: {len(recent_news)} 条")
            
            # 测试重复保存（应该被去重）
            print("🔍 测试重复新闻去重...")
            duplicate_saved = db_manager.save_news_items_batch(test_news[:2])
            print(f"   重复保存结果: {duplicate_saved} 条（应该为0）")
            
            result = {
                "status": "success",
                "test_news_count": len(test_news),
                "saved_count": saved_count,
                "retrieved_count": len(retrieved_news),
                "recent_count": len(recent_news),
                "duplicate_saved": duplicate_saved,
                "deduplication_works": duplicate_saved == 0
            }
            
            self.results["news_operations"] = result
            return result
            
        except Exception as e:
            print(f"❌ 新闻数据操作测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["news_operations"] = result
            return result

    def test_analysis_operations(self) -> Dict[str, any]:
        """测试分析结果操作"""
        print("\n🤖 测试分析结果操作")
        print("-" * 60)
        
        try:
            # 确保有新闻数据
            news_items = db_manager.get_news_items(limit=3)
            if not news_items:
                print("⚠️  没有新闻数据，先创建一些测试新闻")
                test_news = self._create_test_news_items()[:3]
                db_manager.save_news_items_batch(test_news)
                news_items = db_manager.get_news_items(limit=3)
            
            # 创建测试分析结果
            test_results = self._create_test_analysis_results(news_items)
            print(f"🔍 创建了 {len(test_results)} 条测试分析结果")
            
            # 测试保存分析结果（暂未实现）
            print("🔍 测试保存分析结果...")
            saved_count = 0  # 暂未实现分析结果保存
            print(f"   保存功能暂未实现: {len(test_results)} 条")
            
            # 测试查询分析结果（暂未实现）
            print("🔍 测试查询分析结果...")
            retrieved_results = []  # 暂未实现分析结果查询
            print(f"   查询功能暂未实现: {len(retrieved_results)} 条分析结果")
            
            # 测试最近分析结果查询
            print("🔍 测试最近分析结果查询...")
            # 暂时跳过分析结果查询，因为数据库中没有相关表
            recent_results = []
            print(f"   最近1小时分析结果: {len(recent_results)} 条（暂未实现）")
            
            result = {
                "status": "success",
                "test_results_count": len(test_results),
                "saved_count": saved_count,
                "retrieved_count": len(retrieved_results),
                "recent_count": len(recent_results)
            }
            
            self.results["analysis_operations"] = result
            return result
            
        except Exception as e:
            print(f"❌ 分析结果操作测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["analysis_operations"] = result
            return result

    def test_data_maintenance(self) -> Dict[str, any]:
        """测试数据维护功能"""
        print("\n🧹 测试数据维护功能")
        print("-" * 60)
        
        try:
            # 获取清理前的统计
            initial_stats = db_manager.get_stats()
            print(f"🔍 清理前统计: {initial_stats}")
            
            # 创建一些旧数据
            print("🔍 创建旧数据用于清理测试...")
            old_news = self._create_old_news_items()
            db_manager.save_news_items_batch(old_news)
            
            # 获取添加旧数据后的统计
            before_cleanup_stats = db_manager.get_stats()
            print(f"   添加旧数据后: {before_cleanup_stats}")
            
            # 测试数据清理
            print("🔍 测试数据清理功能...")
            cleaned_count = db_manager.cleanup_old_data()
            print(f"   清理了 {cleaned_count} 条旧数据")
            
            # 获取清理后的统计
            after_cleanup_stats = db_manager.get_stats()
            print(f"   清理后统计: {after_cleanup_stats}")
            
            # 测试数据库优化
            print("🔍 测试数据库优化...")
            db_manager.optimize_database()
            print("✅ 数据库优化完成")
            
            result = {
                "status": "success",
                "initial_stats": initial_stats,
                "before_cleanup_stats": before_cleanup_stats,
                "cleaned_count": cleaned_count,
                "after_cleanup_stats": after_cleanup_stats
            }
            
            self.results["data_maintenance"] = result
            return result
            
        except Exception as e:
            print(f"❌ 数据维护测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["data_maintenance"] = result
            return result

    def test_statistics(self) -> Dict[str, any]:
        """测试统计功能"""
        print("\n📊 测试统计功能")
        print("-" * 60)
        
        try:
            # 测试基本统计
            print("🔍 测试基本统计...")
            stats = db_manager.get_stats()
            print(f"   基本统计: {stats}")
            
            # 测试基本统计
            print("🔍 测试基本统计...")
            basic_stats = db_manager.get_stats()
            print(f"   基本统计: {basic_stats}")
            
            # 其他统计功能暂未实现
            collection_stats = {"note": "收集统计功能暂未实现"}
            analysis_stats = {"note": "分析统计功能暂未实现"}
            
            result = {
                "status": "success",
                "basic_stats": basic_stats,
                "collection_stats": collection_stats,
                "analysis_stats": analysis_stats
            }
            
            self.results["statistics"] = result
            return result
            
        except Exception as e:
            print(f"❌ 统计功能测试失败: {e}")
            result = {"status": "failed", "error": str(e)}
            self.results["statistics"] = result
            return result

    def _create_test_news_items(self) -> List[NewsItem]:
        """创建测试新闻数据"""
        test_news = []
        
        test_data = [
            ("A股三大指数集体上涨", "股市", "东方财富"),
            ("央行降准释放流动性", "货币政策", "新浪财经"),
            ("科技股表现强劲", "科技", "腾讯财经"),
            ("房地产政策调整", "房地产", "财经网"),
            ("新能源汽车销量增长", "汽车", "证券时报")
        ]
        
        for i, (title, category, source) in enumerate(test_data):
            news = NewsItem()
            news.title = title
            news.content = f"这是关于{title}的详细内容。包含了相关的市场分析和数据。"
            news.source = source
            news.category = category
            news.url = f"https://test.com/news/{i+1}"
            news.publish_time = datetime.now()
            news.keywords = ["测试", "财经", category]
            test_news.append(news)
            
        return test_news

    def _create_old_news_items(self) -> List[NewsItem]:
        """创建旧新闻数据（用于清理测试）"""
        old_news = []
        
        # 创建10天前的新闻
        old_date = datetime.now() - timedelta(days=10)
        
        for i in range(3):
            news = NewsItem()
            news.title = f"旧新闻标题 {i+1}"
            news.content = f"这是第{i+1}条旧新闻的内容"
            news.source = "旧新闻源"
            news.category = "旧分类"
            news.url = f"https://old.com/news/{i+1}"
            news.publish_time = old_date
            news.keywords = ["旧", "清理测试"]
            old_news.append(news)
            
        return old_news

    def _create_test_analysis_results(self, news_items: List[NewsItem]) -> List[AnalysisResult]:
        """创建测试分析结果"""
        results = []
        
        sectors_list = [
            ["银行", "金融", "保险"],
            ["科技", "软件", "互联网"],
            ["新能源", "汽车", "制造"]
        ]
        
        sentiments = ["积极", "中性", "消极"]
        
        for i, news in enumerate(news_items):
            result = AnalysisResult(
                news_id=str(news.id if hasattr(news, 'id') and news.id else i + 1),
                affected_sectors=sectors_list[i % len(sectors_list)],
                impact_score=7.5 + (i * 0.5),  # 7.5, 8.0, 8.5
                impact_level="中等",
                sentiment=sentiments[i % len(sentiments)],
                summary=f"对{news.title}的分析结果",
                recommendation=f"建议{i+1}",
                analysis_time=datetime.now()
            )
            results.append(result)
            
        return results

    def run_all_tests(self) -> Dict[str, dict]:
        """运行所有测试"""
        print("🧪 数据库功能测试")
        print("=" * 80)
        
        try:
            # 设置测试环境
            self.setup_test_database()
            
            # 1. 测试数据库初始化
            self.test_database_initialization()
            
            # 2. 测试新闻操作
            self.test_news_operations()
            
            # 3. 测试分析结果操作
            self.test_analysis_operations()
            
            # 4. 测试统计功能
            self.test_statistics()
            
            # 5. 测试数据维护
            self.test_data_maintenance()
            
            # 显示测试总结
            self.print_summary()
            
        finally:
            # 清理测试环境
            self.cleanup_test_database()
            
        return self.results

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📋 数据库测试总结")
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
                if test_name == "news_operations":
                    count = result.get("saved_count", 0)
                    dedup = result.get("deduplication_works", False)
                    print(f"   保存了 {count} 条新闻，去重功能: {'正常' if dedup else '异常'}")
                elif test_name == "data_maintenance":
                    cleaned = result.get("cleaned_count", 0)
                    print(f"   清理了 {cleaned} 条旧数据")


def run_database_tests():
    """运行数据库测试的主函数"""
    tester = DatabaseTester()
    results = tester.run_all_tests()
    return results


if __name__ == "__main__":
    run_database_tests() 