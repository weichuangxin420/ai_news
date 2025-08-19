#!/usr/bin/env python3
"""
API数据源测试模块
测试各个API数据源的连接和数据获取功能
"""

import json
import os
import sys
import time
from typing import Dict, Tuple

import requests
import yaml

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import get_logger

logger = get_logger("test_api")


class APITester:
    """API测试器"""
    
    def __init__(self):
        """初始化API测试器"""
        self.config = self._load_config()
        self.results = {}
        
    def _load_config(self) -> dict:
        """加载配置文件"""
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config", "config.yaml")
        template_path = os.path.join(project_root, "config", "config.yaml.template")
        
        # 优先使用实际配置文件，否则使用模板
        if os.path.exists(config_path):
            path = config_path
        elif os.path.exists(template_path):
            path = template_path
        else:
            print("❌ 未找到配置文件")
            return {}
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}

    def test_all_apis(self) -> Dict[str, dict]:
        """测试所有API源"""
        print("\n🔌 测试API数据源")
        print("-" * 60)
        
        api_sources = self.config.get("news_collection", {}).get("sources", {}).get("api_sources", {})
        
        for api_name, api_config in api_sources.items():
            if not api_config.get("enabled", False):
                print(f"⚠️  {api_name:20} | 已禁用")
                self.results[api_name] = {"status": "disabled"}
                continue
                
            print(f"🔍 {api_name:20} | 测试中...", end="", flush=True)
            
            try:
                success, data_count, response_time = self._test_single_api(api_name, api_config)
                
                if success:
                    print(f"\r✅ {api_name:20} | 连接正常 | {data_count}条数据 | {response_time:.2f}s")
                    self.results[api_name] = {
                        "status": "success",
                        "data_count": data_count,
                        "response_time": response_time
                    }
                else:
                    print(f"\r❌ {api_name:20} | 连接失败")
                    self.results[api_name] = {
                        "status": "failed",
                        "error": "connection_failed"
                    }
                    
            except Exception as e:
                print(f"\r❌ {api_name:20} | 异常: {str(e)[:30]}")
                self.results[api_name] = {
                    "status": "error",
                    "error": str(e)
                }
                
            time.sleep(1)  # 避免请求过于频繁
            
        return self.results

    def _test_single_api(self, api_name: str, api_config: dict) -> Tuple[bool, int, float]:
        """测试单个API源"""
        base_url = api_config.get("base_url", "")
        timeout = 10
        
        start_time = time.time()
        
        try:
            if api_name == "eastmoney":
                # 测试东方财富API
                params = api_config.get("params", {})
                response = requests.get(base_url, params=params, timeout=timeout)
                response.raise_for_status()
                
                content = response.text
                if content.startswith("jQuery"):
                    start = content.find("(") + 1
                    end = content.rfind(")")
                    json_str = content[start:end]
                    data = json.loads(json_str)
                    
                    if "data" in data and "diff" in data["data"]:
                        response_time = time.time() - start_time
                        return True, len(data["data"]["diff"]), response_time
                        
            elif api_name == "tencent_finance":
                # 测试腾讯财经API
                symbols = ["s_sh000001", "s_sz399001"]
                url = base_url + ",".join(symbols)
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                data_count = len([line for line in lines if line.startswith('v_')])
                response_time = time.time() - start_time
                return True, data_count, response_time
                
            elif api_name == "sina_finance":
                # 测试新浪财经API
                symbols = ["sh000001", "sz399001"]
                url = base_url + ",".join(symbols)
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                data_count = len([line for line in lines if 'hq_str_' in line])
                response_time = time.time() - start_time
                return True, data_count, response_time
                
        except Exception as e:
            response_time = time.time() - start_time
            raise e
            
        return False, 0, 0

    def test_specific_api(self, api_name: str) -> Dict[str, dict]:
        """测试指定的API"""
        api_sources = self.config.get("news_collection", {}).get("sources", {}).get("api_sources", {})
        
        if api_name not in api_sources:
            print(f"❌ 未找到API: {api_name}")
            return {}
            
        api_config = api_sources[api_name]
        
        if not api_config.get("enabled", False):
            print(f"⚠️  API {api_name} 已禁用")
            return {api_name: {"status": "disabled"}}
            
        print(f"🔍 测试 {api_name}...")
        
        try:
            success, data_count, response_time = self._test_single_api(api_name, api_config)
            
            if success:
                print(f"✅ {api_name} 测试成功")
                print(f"   数据量: {data_count}条")
                print(f"   响应时间: {response_time:.2f}秒")
                
                result = {
                    "status": "success",
                    "data_count": data_count,
                    "response_time": response_time
                }
            else:
                print(f"❌ {api_name} 测试失败")
                result = {"status": "failed", "error": "connection_failed"}
                
        except Exception as e:
            print(f"❌ {api_name} 测试异常: {e}")
            result = {"status": "error", "error": str(e)}
            
        return {api_name: result}

    def get_test_summary(self) -> dict:
        """获取测试总结"""
        if not self.results:
            return {}
            
        total = len(self.results)
        success = len([r for r in self.results.values() if r.get("status") == "success"])
        failed = len([r for r in self.results.values() if r.get("status") == "failed"])
        error = len([r for r in self.results.values() if r.get("status") == "error"])
        disabled = len([r for r in self.results.values() if r.get("status") == "disabled"])
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "error": error,
            "disabled": disabled,
            "success_rate": success / max(total - disabled, 1) * 100
        }

    def print_summary(self):
        """打印测试总结"""
        summary = self.get_test_summary()
        
        if not summary:
            print("⚠️  没有测试结果")
            return
            
        print(f"\n📊 API测试总结:")
        print(f"   总数: {summary['total']}")
        print(f"   成功: {summary['success']}")
        print(f"   失败: {summary['failed']}")
        print(f"   异常: {summary['error']}")
        print(f"   禁用: {summary['disabled']}")
        print(f"   成功率: {summary['success_rate']:.1f}%")


def run_api_tests():
    """运行API测试的主函数"""
    tester = APITester()
    results = tester.test_all_apis()
    tester.print_summary()
    return results


if __name__ == "__main__":
    run_api_tests() 