#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import os

def parse_launcher_xml(xml_file_path):
    """
    解析launcher.xml文件，提取ConfigCamera.VehicleModelView.TranslationVehicleModelView.Z的值
    
    参数:
        xml_file_path: XML文件的路径
        
    返回:
        成功时返回Z节点的浮点数值，失败时返回None
    """
    try:
        # 检查文件是否存在
        if not os.path.isfile(xml_file_path):
            print(f"错误: 文件 '{xml_file_path}' 不存在")
            return None
            
        # 解析XML文件
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # 查找ConfigCamera节点
        config_camera = root.find('ConfigCamera')
        if config_camera is None:
            print("错误: 未找到ConfigCamera节点")
            return None
            
        # 查找VehicleModelView节点
        vehicle_model_view = config_camera.find('VehicleModelView')
        if vehicle_model_view is None:
            print("错误: 未找到VehicleModelView节点")
            return None
            
        # 查找TranslationVehicleModelView节点
        translation_vehicle_model_view = vehicle_model_view.find('TranslationVehicleModelView')
        if translation_vehicle_model_view is None:
            print("错误: 未找到TranslationVehicleModelView节点")
            return None
            
        # 查找Z节点
        z_element = translation_vehicle_model_view.find('Z')
        if z_element is None:
            print("错误: 未找到Z节点")
            return None
            
        # 获取Z节点的文本内容并修剪空白字符
        z_text = z_element.text
        if z_text is None:
            print("错误: Z节点没有文本内容")
            return None
            
        z_text = z_text.strip()
        print(f"Z节点的原始文本内容: '{z_text}'")
        
        # 转换为浮点数
        try:
            z_value = float(z_text)
            print(f"成功解析Z值: {z_value}")
            return z_value
        except ValueError:
            print(f"错误: 无法将 '{z_text}' 转换为浮点数")
            return None
            
    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None

if __name__ == "__main__":
    # XML文件路径
    xml_file = r"/Users/stanleysun/Downloads/launcher.xml"
    
    # 解析XML文件并获取Z值
    z_value = parse_launcher_xml(xml_file)
    
    if z_value is not None:
        print(f"\n最终结果: ConfigCamera.VehicleModelView.TranslationVehicleModelView.Z = {z_value}")
    else:
        print("\n未能成功解析Z值")