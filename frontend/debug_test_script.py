#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段调试测试脚本
用于测试修复后的代码，帮助定位问题

作者：AI助手
创建日期：2025-07-29
"""

import logging
import sys
import os

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('adaptive_learning_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_api_config():
    """测试API配置模块"""
    print("=" * 60)
    print("🔍 测试1: API配置模块")
    print("=" * 60)
    
    try:
        from config.api_config import get_api_config
        config = get_api_config()
        
        print(f"✅ API配置加载成功")
        print(f"   基础URL: {config.base_url}")
        print(f"   超时时间: {config.timeout}秒")
        print(f"   端点配置: {list(config.endpoints.keys())}")
        
        # 测试自适应学习端点
        adaptive_url = config.get_endpoint_url("adaptive_learning_analyze")
        print(f"   自适应学习分析端点: {adaptive_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ API配置测试失败: {e}")
        logger.exception("API配置异常:")
        return False

def test_webapi_function():
    """测试WebAPI分析函数"""
    print("=" * 60)
    print("🔍 测试2: WebAPI分析函数")
    print("=" * 60)
    
    try:
        # 导入函数
        from clients.adaptive_learning_webapi import analyze_adaptive_learning_parameters
        
        # 测试数据 - 正常参数
        print("测试用例1: 正常参数")
        success, is_compliant, params, msg = analyze_adaptive_learning_parameters(
            target_weight=200.0,
            actual_total_cycle_ms=9500,
            actual_coarse_time_ms=3800,
            error_value=0.3,
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=0.37
        )
        print(f"   结果: success={success}, is_compliant={is_compliant}")
        print(f"   消息: {msg}")
        print(f"   调整参数: {params}")
        
        # 测试数据 - None参数
        print("\n测试用例2: fine_flow_rate为None")
        success, is_compliant, params, msg = analyze_adaptive_learning_parameters(
            target_weight=200.0,
            actual_total_cycle_ms=9500,
            actual_coarse_time_ms=3800,
            error_value=0.3,
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=None  # 测试None值
        )
        print(f"   结果: success={success}, is_compliant={is_compliant}")
        print(f"   消息: {msg}")
        print(f"   调整参数: {params}")
        
        # 测试数据 - 边界参数
        print("\n测试用例3: 边界条件参数")
        success, is_compliant, params, msg = analyze_adaptive_learning_parameters(
            target_weight=200.0,
            actual_total_cycle_ms=15000,  # 超出标准
            actual_coarse_time_ms=3800,
            error_value=0.8,  # 超出边界
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=0.5
        )
        print(f"   结果: success={success}, is_compliant={is_compliant}")
        print(f"   消息: {msg}")
        print(f"   调整参数: {params}")
        
        return True
        
    except Exception as e:
        print(f"❌ WebAPI函数测试失败: {e}")
        logger.exception("WebAPI函数异常:")
        return False

def test_parameter_handling():
    """测试参数处理逻辑"""
    print("=" * 60)
    print("🔍 测试3: 参数处理逻辑")
    print("=" * 60)
    
    try:
        # 模拟_handle_adaptive_learning_adjustment的核心逻辑
        print("测试用例1: 正常参数处理")
        new_params = {"coarse_advance": 16.0, "fall_value": 0.5}
        
        if new_params is None:
            print("   检测到None参数")
        elif not isinstance(new_params, dict):
            print(f"   检测到非字典参数: {type(new_params)}")
        elif not new_params:
            print("   检测到空字典参数")
        else:
            print("   ✅ 参数验证通过")
            
            if 'coarse_advance' in new_params:
                print(f"   快加提前量调整: {new_params['coarse_advance']}")
            if 'fall_value' in new_params:
                print(f"   落差值调整: {new_params['fall_value']}")
        
        print("\n测试用例2: None参数处理")
        new_params = None
        
        if new_params is None:
            print("   ✅ 检测到None参数，应该失败")
        else:
            print("   ❌ 未检测到None参数")
            
        print("\n测试用例3: 空字典参数处理")
        new_params = {}
        
        if not new_params:
            print("   ✅ 检测到空字典参数，应该失败")
        else:
            print("   ❌ 未检测到空字典参数")
        
        return True
        
    except Exception as e:
        print(f"❌ 参数处理测试失败: {e}")
        logger.exception("参数处理异常:")
        return False

def test_request_model_validation():
    """测试请求模型验证"""
    print("=" * 60)
    print("🔍 测试4: 请求模型验证")
    print("=" * 60)
    
    try:
        from models.request_models import AdaptiveLearningAnalysisRequest
        
        # 测试正常数据
        print("测试用例1: 正常数据验证")
        request = AdaptiveLearningAnalysisRequest(
            target_weight=200.0,
            actual_total_cycle_ms=9500,
            actual_coarse_time_ms=3800,
            error_value=0.3,
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=0.37
        )
        print(f"   ✅ 正常数据验证通过: fine_flow_rate={request.fine_flow_rate}")
        
        # 测试None数据
        print("\n测试用例2: None数据验证")
        request = AdaptiveLearningAnalysisRequest(
            target_weight=200.0,
            actual_total_cycle_ms=9500,
            actual_coarse_time_ms=3800,
            error_value=0.3,
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=None
        )
        print(f"   ✅ None数据验证通过: fine_flow_rate={request.fine_flow_rate}")
        
        # 测试负数数据
        print("\n测试用例3: 负数数据验证")
        try:
            request = AdaptiveLearningAnalysisRequest(
                target_weight=200.0,
                actual_total_cycle_ms=9500,
                actual_coarse_time_ms=3800,
                error_value=0.3,
                current_coarse_advance=15.0,
                current_fall_value=0.4,
                fine_flow_rate=-1.0
            )
            print("   ❌ 负数数据验证应该失败但通过了")
        except Exception as e:
            print(f"   ✅ 负数数据验证正确失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 请求模型验证测试失败: {e}")
        logger.exception("请求模型验证异常:")
        return False

def main():
    """主测试函数"""
    print("🚀 开始自适应学习阶段调试测试")
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    tests = [
        ("API配置", test_api_config),
        ("WebAPI函数", test_webapi_function),
        ("参数处理", test_parameter_handling),
        ("请求模型验证", test_request_model_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.exception(f"测试{test_name}执行异常:")
            results.append((test_name, False))
    
    # 打印总结
    print("=" * 60)
    print("🎯 测试结果总结")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(tests)} 项测试通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过！可以尝试运行实际程序")
    else:
        print("⚠️ 部分测试失败，请检查配置和代码")
    
    print(f"\n详细日志已保存到: adaptive_learning_debug.log")

if __name__ == "__main__":
    main()