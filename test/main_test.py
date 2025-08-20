#!/usr/bin/env python3
"""
AI新闻系统 - 主测试入口
统一管理和执行各个模块的测试
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from test_api import run_api_tests
from test_news_collection import run_news_collection_tests
from test_ai_analysis import run_ai_analysis_tests
from test_database import run_database_tests

# 并发分析功能已集成到主AI分析器中，无需单独测试模块
CONCURRENT_AVAILABLE = False


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        """初始化测试运行器"""
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_api_tests(self) -> Dict[str, dict]:
        """运行API测试"""
        print("🔌 运行API数据源测试")
        print("=" * 80)
        
        try:
            results = run_api_tests()
            self.results["api_tests"] = {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            return results
        except Exception as e:
            print(f"❌ API测试运行失败: {e}")
            self.results["api_tests"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return {}
    
    def run_news_collection_tests(self) -> Dict[str, dict]:
        """运行新闻收集测试"""
        print("\n📰 运行新闻收集测试")
        print("=" * 80)
        
        try:
            results = run_news_collection_tests()
            self.results["news_collection_tests"] = {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            return results
        except Exception as e:
            print(f"❌ 新闻收集测试运行失败: {e}")
            self.results["news_collection_tests"] = {
                "status": "failed", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return {}
    
    def run_ai_analysis_tests(self) -> Dict[str, dict]:
        """运行AI分析测试"""
        print("\n🤖 运行AI分析测试")
        print("=" * 80)
        
        try:
            results = run_ai_analysis_tests()
            self.results["ai_analysis_tests"] = {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            return results
        except Exception as e:
            print(f"❌ AI分析测试运行失败: {e}")
            self.results["ai_analysis_tests"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return {}
    
    def run_database_tests(self) -> Dict[str, dict]:
        """运行数据库测试"""
        print("\n💾 运行数据库测试")
        print("=" * 80)
        
        try:
            results = run_database_tests()
            self.results["database_tests"] = {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            return results
        except Exception as e:
            print(f"❌ 数据库测试运行失败: {e}")
            self.results["database_tests"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return {}
    

    
    def run_all_tests(self) -> Dict[str, dict]:
        """运行所有测试"""
        print("🚀 AI新闻系统 - 完整测试套件")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # 1. API数据源测试
        self.run_api_tests()
        
        # 2. 数据库测试
        self.run_database_tests()
        
        # 3. 新闻收集测试
        self.run_news_collection_tests()
        
        # 4. AI分析测试（包含并发功能测试）
        self.run_ai_analysis_tests()
        
        self.end_time = time.time()
        
        # 显示总结
        self.print_final_summary()
        
        # 保存测试结果
        self.save_test_results()
        
        return self.results
    
    def run_specific_test(self, test_name: str) -> Dict[str, dict]:
        """运行特定测试"""
        test_map = {
            "api": self.run_api_tests,
            "collection": self.run_news_collection_tests,
            "analysis": self.run_ai_analysis_tests,
            "database": self.run_database_tests
        }
        

        
        if test_name not in test_map:
            print(f"❌ 未知的测试模块: {test_name}")
            print(f"可用的测试模块: {', '.join(test_map.keys())}")
            return {}
        
        self.start_time = time.time()
        results = test_map[test_name]()
        self.end_time = time.time()
        
        self.print_final_summary()
        self.save_test_results()
        
        return results
    
    def print_final_summary(self):
        """打印最终测试总结"""
        if not self.results:
            return
            
        print("\n" + "=" * 80)
        print("🎯 测试总结报告")
        print("=" * 80)
        
        # 计算总体统计
        total_modules = len(self.results)
        completed_modules = len([r for r in self.results.values() if r["status"] == "completed"])
        failed_modules = total_modules - completed_modules
        
        # 运行时间
        if self.start_time and self.end_time:
            total_time = self.end_time - self.start_time
            print(f"⏱️  总运行时间: {total_time:.2f}秒")
        
        print(f"📊 模块统计:")
        print(f"   总模块数: {total_modules}")
        print(f"   完成模块: {completed_modules}")
        print(f"   失败模块: {failed_modules}")
        print(f"   成功率: {completed_modules/max(total_modules,1)*100:.1f}%")
        
        print(f"\n📋 模块详情:")
        
        for module_name, module_result in self.results.items():
            status_icon = "✅" if module_result["status"] == "completed" else "❌"
            module_display_name = {
                "api_tests": "API数据源测试",
                "news_collection_tests": "新闻收集测试", 
                "ai_analysis_tests": "AI分析测试",
                "database_tests": "数据库测试"
            }.get(module_name, module_name)
            
            print(f"{status_icon} {module_display_name}")
            
            if module_result["status"] == "completed":
                # 显示各模块内部的详细统计
                inner_results = module_result.get("results", {})
                if inner_results:
                    success_count = len([r for r in inner_results.values() if r.get("status") == "success"])
                    total_count = len(inner_results)
                    print(f"     内部测试: {success_count}/{total_count} 通过")
            else:
                error = module_result.get("error", "未知错误")
                print(f"     错误: {error}")
        
        # 推荐下一步操作
        print(f"\n💡 建议:")
        if failed_modules > 0:
            print(f"   - 检查失败的模块，修复相关问题")
            print(f"   - 确保虚拟环境已激活且依赖已安装")
            print(f"   - 检查配置文件是否正确设置")
        else:
            print(f"   - 所有测试通过！系统准备就绪")
            print(f"   - 可以开始正式运行新闻收集系统")
    
    def save_test_results(self, filename: Optional[str] = None):
        """保存测试结果到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 保存到logs文件夹
            logs_dir = "data/logs"
            os.makedirs(logs_dir, exist_ok=True)
            filename = os.path.join(logs_dir, f"test_results_{timestamp}.json")
        
        try:
            # 添加元数据
            output_data = {
                "test_metadata": {
                    "run_time": datetime.now().isoformat(),
                    "total_time": self.end_time - self.start_time if self.start_time and self.end_time else 0,
                    "python_version": sys.version,
                    "platform": sys.platform
                },
                "test_results": self.results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 测试结果已保存到: {filename}")
            
        except Exception as e:
            print(f"⚠️  保存测试结果失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI新闻系统测试套件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试模块说明:
  api         - 测试API数据源连接和数据获取
  collection  - 测试新闻收集功能
  analysis    - 测试AI分析功能

  database    - 测试数据库操作
  all         - 运行所有测试（默认）

使用示例:
  python main_test.py                    # 运行所有测试
  python main_test.py --module api       # 只测试API
  python main_test.py --module database  # 只测试数据库
  python main_test.py --save results.json # 保存结果到logs文件夹中的指定文件
        """
    )
    
    parser.add_argument(
        '--module', '-m',
        choices=['api', 'collection', 'analysis', 'database', 'all'],
        default='all',
        help='指定要运行的测试模块'
    )
    
    parser.add_argument(
        '--save', '-s',
        type=str,
        help='指定保存测试结果的文件名'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='安静模式，减少输出'
    )
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = TestRunner()
    
    try:
        # 运行测试
        if args.module == 'all':
            runner.run_all_tests()
        else:
            runner.run_specific_test(args.module)
        
        # 自定义保存文件名
        if args.save:
            # 如果用户指定的是相对路径文件名，也保存到logs文件夹
            save_path = args.save
            if not os.path.isabs(save_path) and not save_path.startswith("data/logs/"):
                logs_dir = "data/logs"
                os.makedirs(logs_dir, exist_ok=True)
                save_path = os.path.join(logs_dir, save_path)
            runner.save_test_results(save_path)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 