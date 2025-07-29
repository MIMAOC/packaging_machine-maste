#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSL握手详细诊断工具
深度分析SSL连接失败的原因
"""

import socket
import ssl
import sys
import time
from typing import Dict, Any
import requests
import urllib3

# 禁用警告
urllib3.disable_warnings()

def analyze_ssl_handshake(host: str, port: int) -> Dict[str, Any]:
    """分析SSL握手过程"""
    
    results = {
        'tcp_connection': False,
        'ssl_handshake': False,
        'ssl_info': {},
        'error_details': {},
        'supported_protocols': [],
        'supported_ciphers': []
    }
    
    print(f"🔍 开始分析 {host}:{port}")
    
    # 1. 测试TCP连接
    print("\n1️⃣ 测试TCP连接...")
    try:
        sock = socket.create_connection((host, port), timeout=10)
        results['tcp_connection'] = True
        print("✅ TCP连接成功")
        sock.close()
    except Exception as e:
        results['error_details']['tcp'] = str(e)
        print(f"❌ TCP连接失败: {e}")
        return results
    
    # 2. 测试不同SSL/TLS版本
    print("\n2️⃣ 测试SSL/TLS协议版本...")
    protocols = [
        ('TLS 1.3', ssl.PROTOCOL_TLS),
        ('TLS 1.2', ssl.PROTOCOL_TLSv1_2),
        ('TLS 1.1', ssl.PROTOCOL_TLSv1_1),
        ('TLS 1.0', ssl.PROTOCOL_TLSv1),
    ]
    
    for proto_name, proto_const in protocols:
        try:
            context = ssl.SSLContext(proto_const)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    results['supported_protocols'].append(proto_name)
                    print(f"✅ {proto_name} 支持")
                    
                    if not results['ssl_handshake']:
                        results['ssl_handshake'] = True
                        results['ssl_info'] = {
                            'protocol': ssock.version(),
                            'cipher': ssock.cipher(),
                            'server_cert': ssock.getpeercert_chain()[0].subject if ssock.getpeercert_chain() else None
                        }
                    break
                    
        except Exception as e:
            print(f"❌ {proto_name} 失败: {e}")
            results['error_details'][proto_name] = str(e)
    
    # 3. 详细SSL上下文测试
    print("\n3️⃣ 详细SSL上下文测试...")
    try:
        # 创建最宽松的SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ALL:@SECLEVEL=0')
        
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print("✅ 宽松SSL上下文成功")
                results['ssl_handshake'] = True
                
                # 获取详细信息
                print(f"协议版本: {ssock.version()}")
                print(f"加密套件: {ssock.cipher()}")
                print(f"服务器证书主题: {ssock.getpeercert().get('subject', 'N/A')}")
                
    except Exception as e:
        print(f"❌ 宽松SSL上下文失败: {e}")
        results['error_details']['ssl_context'] = str(e)
    
    # 4. OpenSSL命令行等效测试
    print("\n4️⃣ 模拟OpenSSL s_client...")
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('DEFAULT')
        
        sock = socket.create_connection((host, port), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=host)
        
        # 发送HTTP请求测试
        request = f"GET /api/health HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        ssock.send(request.encode())
        
        response = ssock.recv(4096).decode('utf-8', errors='ignore')
        print("✅ SSL + HTTP请求成功")
        print(f"响应前100字符: {response[:100]}")
        
        ssock.close()
        
    except Exception as e:
        print(f"❌ SSL + HTTP请求失败: {e}")
        results['error_details']['ssl_http'] = str(e)
    
    return results

def test_python_requests_debug():
    """测试Python requests的详细调试"""
    print("\n🐍 Python requests详细调试...")
    
    # 启用详细的HTTP调试
    import logging
    import http.client as http_client
    
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    
    try:
        response = requests.get(
            'https://guji.xiaoajia.cn:8443/api/health',
            verify=False,
            timeout=30,
            stream=True
        )
        print(f"✅ requests成功: {response.status_code}")
        
    except Exception as e:
        print(f"❌ requests失败: {e}")
        print(f"异常类型: {type(e).__name__}")

if __name__ == "__main__":
    # 分析SSL握手
    results = analyze_ssl_handshake('guji.xiaoajia.cn', 8443)
    
    print("\n📊 诊断结果汇总:")
    print(f"TCP连接: {'✅' if results['tcp_connection'] else '❌'}")
    print(f"SSL握手: {'✅' if results['ssl_handshake'] else '❌'}")
    print(f"支持的协议: {', '.join(results['supported_protocols'])}")
    
    if results['error_details']:
        print("\n❌ 错误详情:")
        for key, error in results['error_details'].items():
            print(f"  {key}: {error}")
    
    # 测试requests调试
    test_python_requests_debug()