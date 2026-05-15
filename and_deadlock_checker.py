#!/usr/bin/env python3
"""
Android进程死锁检测脚本
用于检测Android设备上进程的死锁和卡死问题
"""

import subprocess
import sys
import re
from datetime import datetime
from typing import List, Tuple, Optional, Dict

class AndroidDeadlockDetector:
    def __init__(self):
        self.report_lines = []
        self.has_issues = False
        
    def log(self, message: str, level: str = "INFO"):
        """添加日志信息"""
        prefix = {
            "INFO": "[INFO]",
            "WARNING": "[WARNING]",
            "ERROR": "[ERROR]",
            "SUCCESS": "[SUCCESS]"
        }.get(level, "[INFO]")
        
        formatted_message = f"{prefix} {message}"
        print(formatted_message)
        self.report_lines.append(formatted_message)
        
    def run_adb_command(self, command: str) -> Tuple[bool, str]:
        """执行ADB命令并返回结果"""
        try:
            result = subprocess.run(
                f"adb {command}", 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Command failed: {str(e)}"
    
    def check_adb_connection(self) -> bool:
        """检查ADB连接是否正常"""
        self.log("检查ADB连接...")
        success, output = self.run_adb_command("devices")
        
        if not success:
            self.log("ADB命令执行失败", "ERROR")
            return False
            
        # 检查是否有已连接的设备
        devices = [line for line in output.split('\n') if '\tdevice' in line]
        
        if not devices:
            self.log("未找到已连接的Android设备", "ERROR")
            self.log("请确保:")
            self.log("1. USB调试已开启")
            self.log("2. 设备已通过USB连接")
            self.log("3. 电脑已授权设备调试")
            return False
            
        self.log(f"找到 {len(devices)} 个设备", "SUCCESS")
        return True
    
    def get_process_pid(self, target: str) -> Optional[str]:
        """获取进程的PID"""
        self.log(f"查找进程: {target}")
        
        # 尝试通过ps命令查找进程
        success, output = self.run_adb_command(f"shell ps | grep {target}")
        
        if not success or not output.strip():
            self.log(f"未找到进程: {target}", "ERROR")
            return None
            
        # 解析输出获取PID
        lines = output.strip().split('\n')
        for line in lines:
            if target in line and "grep" not in line:
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    self.log(f"找到进程PID: {pid}", "SUCCESS")
                    return pid
                    
        self.log(f"在输出中未找到PID: {output}", "ERROR")
        return None
    
    def check_process_status(self, pid: str) -> int:
        """检查进程状态"""
        self.log("检查进程状态...")
        
        success, output = self.run_adb_command(f"shell cat /proc/{pid}/status")
        
        if not success:
            self.log("无法获取进程状态", "ERROR")
            return 1
            
        # 提取进程状态
        state_match = re.search(r"State:\s+(\w)", output)
        if not state_match:
            self.log("无法解析进程状态", "ERROR")
            return 1
            
        state = state_match.group(1)
        state_descriptions = {
            "R": "运行中",
            "S": "睡眠中(可中断)",
            "D": "不可中断睡眠(通常为I/O操作)",
            "T": "已停止",
            "Z": "僵尸进程"
        }
        
        description = state_descriptions.get(state, "未知状态")
        self.log(f"进程状态: {state} ({description})")
        
        # 返回状态代码
        if state == "D":
            self.log("进程处于不可中断状态，可能是死锁或I/O问题", "WARNING")
            return 2
        elif state == "Z":
            self.log("进程是僵尸进程", "ERROR")
            return 3
        elif state == "T":
            self.log("进程已停止", "WARNING")
            return 4
            
        return 0
    
    def check_threads(self, pid: str) -> int:
        """检查线程状态"""
        self.log("检查线程状态...")
        
        # 获取所有线程ID
        success, output = self.run_adb_command(f"shell ls /proc/{pid}/task/")
        
        if not success or not output.strip():
            self.log("无法获取线程信息", "ERROR")
            return 1
            
        tids = output.strip().split()
        self.log(f"线程数量: {len(tids)}")
        
        # 检查每个线程的状态
        d_count = 0
        r_count = 0
        s_count = 0
        other_count = 0
        
        for tid in tids[:10]:  # 限制检查的线程数量，避免耗时过长
            success, status_output = self.run_adb_command(f"shell cat /proc/{pid}/task/{tid}/status")
            
            if success:
                state_match = re.search(r"State:\s+(\w)", status_output)
                if state_match:
                    state = state_match.group(1)
                    
                    if state == "R":
                        r_count += 1
                    elif state == "S":
                        s_count += 1
                    elif state == "D":
                        d_count += 1
                        self.log(f"警告: 线程 {tid} 处于不可中断状态(D)", "WARNING")
                        
                        # 获取线程调用栈
                        success, stack_output = self.run_adb_command(f"shell cat /proc/{pid}/task/{tid}/stack")
                        if success and stack_output.strip():
                            self.log(f"线程 {tid} 调用栈 (前10行):")
                            for line in stack_output.split('\n')[:10]:
                                self.log(f"  {line}")
                    else:
                        other_count += 1
        
        self.log(f"运行中线程(R): {r_count}")
        self.log(f"睡眠中线程(S): {s_count}")
        self.log(f"不可中断线程(D): {d_count}")
        self.log(f"其他状态线程: {other_count}")
        
        if d_count > 0:
            self.log(f"发现 {d_count} 个线程处于不可中断状态", "WARNING")
            return 1
            
        return 0
    
    def check_anr(self, target: str) -> int:
        """检查ANR痕迹"""
        self.log("检查ANR痕迹...")
        
        # 检查/data/anr目录
        success, output = self.run_adb_command("shell ls -t /data/anr/ 2>/dev/null")
        
        if not success or not output.strip():
            self.log("未发现ANR文件")
            return 0
            
        anr_files = output.strip().split()
        latest_anr = anr_files[0] if anr_files else None
        
        if latest_anr:
            self.log(f"发现ANR文件: {latest_anr}")
            
            # 检查是否与目标进程相关
            success, grep_output = self.run_adb_command(f"shell grep {target} /data/anr/{latest_anr} 2>/dev/null")
            
            if success and grep_output.strip():
                self.log("ANR与目标进程相关", "WARNING")
                
                # 提取关键信息
                success, anr_content = self.run_adb_command(f"shell grep -A5 -B5 {target} /data/anr/{latest_anr} | head -20")
                if success and anr_content.strip():
                    self.log("ANR摘要:")
                    for line in anr_content.split('\n'):
                        self.log(f"  {line}")
                
                return 1
            else:
                self.log("ANR与目标进程无关")
                
        return 0
    
    def check_deadlock_signs(self, pid: str, target: str) -> int:
        """检查死锁迹象"""
        self.log("检查死锁迹象...")
        
        # 检查CPU使用情况
        success, output = self.run_adb_command(f"shell top -n 1 -p {pid} 2>/dev/null")
        
        if success and output.strip():
            lines = output.strip().split('\n')
            if len(lines) > 1:  # 第一行是标题
                cpu_usage = lines[1].split()[8] if len(lines[1].split()) > 8 else "N/A"
                self.log(f"进程CPU使用率: {cpu_usage}%")
                
                if cpu_usage == "0.0":
                    self.log("进程CPU使用率为0%，可能已卡死", "WARNING")
        
        # 检查Binder线程
        success, output = self.run_adb_command(f"shell ps -T -p {pid}")
        
        if success and output.strip():
            binder_threads = [line for line in output.split('\n') if "binder" in line.lower()]
            if binder_threads:
                self.log("Binder线程状态:")
                for thread in binder_threads[:3]:  # 只显示前3个
                    self.log(f"  {thread}")
        
        # 检查锁等待
        success, output = self.run_adb_command(f"shell cat /proc/{pid}/stack 2>/dev/null")
        
        if success and output.strip():
            lock_lines = [line for line in output.split('\n') if "lock" in line.lower() or "mutex" in line.lower()]
            if lock_lines:
                self.log("可能的锁等待:")
                for line in lock_lines[:5]:  # 只显示前5个
                    self.log(f"  {line}")
        
        return 0
    
    def generate_report(self, target: str, pid: str, status_result: int, 
                       threads_result: int, anr_result: int) -> None:
        """生成检测报告"""
        self.log("=" * 50)
        self.log("检测报告")
        self.log("=" * 50)
        self.log(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"目标进程: {target}")
        self.log(f"进程PID: {pid}")
        self.log("")
        
        if status_result != 0 or threads_result != 0 or anr_result != 0:
            self.log("❌ 检测到可能的问题:", "ERROR")
            
            if status_result != 0:
                self.log("- 进程状态异常")
                
            if threads_result != 0:
                self.log("- 有线程处于不可中断状态")
                
            if anr_result != 0:
                self.log("- 发现ANR痕迹")
                
            self.log("")
            self.log("建议操作:")
            self.log("1. 重启应用程序: adb shell am force-stop <包名> && adb shell am start -n <包名>/<主活动>")
            self.log("2. 收集完整日志: adb logcat -d > logcat.txt")
            self.log("3. 获取完整trace: adb bugreport")
            
            self.has_issues = True
        else:
            self.log("✅ 未检测到明显问题", "SUCCESS")
            self.log("")
            self.log("进程状态正常，未发现死锁迹象")
    
    def save_report(self, filename: str = None) -> None:
        """保存报告到文件"""
        if filename is None:
            filename = f"deadlock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
        with open(filename, 'w', encoding='utf-8') as f:
            for line in self.report_lines:
                f.write(line + '\n')
                
        self.log(f"报告已保存至: {filename}")
    
    def run_detection(self, target: str) -> bool:
        """运行完整的检测流程"""
        self.log(f"开始检测进程: {target}")
        
        # 检查ADB连接
        if not self.check_adb_connection():
            return False
            
        # 获取进程PID
        pid = self.get_process_pid(target)
        if pid is None:
            return False
            
        # 执行各项检查
        status_result = self.check_process_status(pid)
        threads_result = self.check_threads(pid)
        anr_result = self.check_anr(target)
        self.check_deadlock_signs(pid, target)
        
        # 生成报告
        self.generate_report(target, pid, status_result, threads_result, anr_result)
        
        # 保存报告
        self.save_report()
        
        return not self.has_issues

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python android_deadlock_detector.py <包名或进程名>")
        print("示例: python android_deadlock_detector.py com.example.app")
        sys.exit(1)
        
    target = sys.argv[1]
    detector = AndroidDeadlockDetector()
    
    try:
        success = detector.run_detection(target)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n检测被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"检测过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()