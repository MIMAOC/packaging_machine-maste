#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
包装机系统数据库和表结构初始化

使用方法：
1. 确保MySQL服务器运行
2. 修改database/db_config.py中的数据库连接配置
3. 运行此脚本：python init_database.py

作者：AI助手
创建日期：2025-08-04
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    print("=" * 60)
    print("🗄️  包装机系统数据库初始化")
    print("=" * 60)
    
    try:
        # 检查数据库模块是否可用
        from database.db_connection import db_manager
        from database.material_dao import MaterialDAO
        
        print("✅ 数据库模块加载成功")
        
        # 测试数据库连接
        print("\n🔍 测试数据库连接...")
        success, message = db_manager.test_connection()
        
        if success:
            print(f"✅ {message}")
            
            # 显示当前物料列表
            print("\n📋 当前物料列表:")
            materials = MaterialDAO.get_all_materials()
            
            if materials:
                print(f"共找到 {len(materials)} 个物料:")
                for i, material in enumerate(materials, 1):
                    status_icon = "✅" if material.is_enabled else "❌"
                    ai_status_icon = {"未学习": "🔄", "已学习": "📚", "已生产": "🏭"}.get(material.ai_status, "❓")
                    print(f"  {i:2d}. {status_icon} {material.material_name}")
                    print(f"      {ai_status_icon} AI状态: {material.ai_status}")
                    print(f"      📅 创建时间: {material.create_time}")
                    print()
            else:
                print("  暂无物料数据")
            
            # 提供一些管理选项
            print("\n⚙️  数据库管理选项:")
            print("1. 添加测试物料")
            print("2. 清空物料表")
            print("3. 显示数据库统计")
            print("4. 退出")
            
            while True:
                try:
                    choice = input("\n请选择操作 (1-4): ").strip()
                    
                    if choice == "1":
                        add_test_materials()
                    elif choice == "2":
                        clear_materials_table()
                    elif choice == "3":
                        show_database_statistics()
                    elif choice == "4":
                        print("👋 再见！")
                        break
                    else:
                        print("❌ 无效选择，请输入1-4")
                        
                except KeyboardInterrupt:
                    print("\n\n👋 用户中断，退出程序")
                    break
                except Exception as e:
                    print(f"❌ 操作异常: {e}")
        else:
            print(f"❌ {message}")
            print("\n🔧 请检查以下配置:")
            print("1. MySQL服务器是否运行")
            print("2. database/db_config.py中的连接配置是否正确")
            print("3. 数据库用户是否有足够权限")
            print("4. 是否已安装PyMySQL: pip install PyMySQL")
            
    except ImportError as e:
        print(f"❌ 导入数据库模块失败: {e}")
        print("\n🔧 请检查:")
        print("1. 是否已安装PyMySQL: pip install PyMySQL")
        print("2. database目录和相关文件是否存在")
        
    except Exception as e:
        print(f"❌ 初始化异常: {e}")

def add_test_materials():
    """添加测试物料"""
    try:
        from database.material_dao import MaterialDAO
        
        test_materials = [
            "测试大米 - 密度1.2g/cm³",
            "测试小麦 - 密度1.4g/cm³",
            "测试花生 - 密度0.8g/cm³",
            "测试芝麻 - 密度0.9g/cm³",
            "测试咖啡豆 - 密度1.1g/cm³"
        ]
        
        print(f"\n🔄 正在添加 {len(test_materials)} 个测试物料...")
        
        success_count = 0
        for material_name in test_materials:
            success, message, material_id = MaterialDAO.create_material(material_name)
            if success:
                print(f"  ✅ {material_name} (ID: {material_id})")
                success_count += 1
            else:
                print(f"  ❌ {material_name}: {message}")
        
        print(f"\n🎉 成功添加 {success_count}/{len(test_materials)} 个测试物料")
        
    except Exception as e:
        print(f"❌ 添加测试物料失败: {e}")

def clear_materials_table():
    """清空物料表"""
    try:
        from database.db_connection import db_manager
        
        confirm = input("\n⚠️  确认要清空物料表吗？这将删除所有物料数据！(y/N): ").strip().lower()
        
        if confirm == 'y':
            affected_rows = db_manager.execute_update("DELETE FROM materials")
            print(f"🗑️  已删除 {affected_rows} 条物料记录")
            
            # 重置自增ID
            db_manager.execute_update("ALTER TABLE materials AUTO_INCREMENT = 1")
            print("🔄 已重置物料表自增ID")
            
        else:
            print("❌ 操作已取消")
            
    except Exception as e:
        print(f"❌ 清空物料表失败: {e}")

def show_database_statistics():
    """显示数据库统计信息"""
    try:
        from database.db_connection import db_manager
        from database.material_dao import MaterialDAO
        
        print("\n📊 数据库统计信息:")
        
        # 总物料数
        total_materials = len(MaterialDAO.get_all_materials(enabled_only=False))
        enabled_materials = len(MaterialDAO.get_all_materials(enabled_only=True))
        disabled_materials = total_materials - enabled_materials
        
        print(f"  📦 总物料数: {total_materials}")
        print(f"  ✅ 启用物料: {enabled_materials}")
        print(f"  ❌ 禁用物料: {disabled_materials}")
        
        # AI状态统计
        unlearned = len(MaterialDAO.get_materials_by_ai_status("未学习", enabled_only=False))
        learned = len(MaterialDAO.get_materials_by_ai_status("已学习", enabled_only=False))
        produced = len(MaterialDAO.get_materials_by_ai_status("已生产", enabled_only=False))
        
        print(f"  🔄 未学习: {unlearned}")
        print(f"  📚 已学习: {learned}")
        print(f"  🏭 已生产: {produced}")
        
        # 数据库基本信息
        db_info = db_manager.execute_query("SELECT DATABASE() as db_name, VERSION() as version")
        if db_info:
            print(f"  🗄️  数据库名: {db_info[0]['db_name']}")
            print(f"  🔢 MySQL版本: {db_info[0]['version']}")
        
        # 表信息
        table_info = db_manager.execute_query("SHOW TABLE STATUS LIKE 'materials'")
        if table_info:
            info = table_info[0]
            print(f"  📊 表引擎: {info['Engine']}")
            print(f"  📏 数据长度: {info['Data_length']} 字节")
            print(f"  📅 创建时间: {info['Create_time']}")
            
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")

if __name__ == "__main__":
    main()