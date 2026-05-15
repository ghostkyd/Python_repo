import subprocess
import sys
import re

def run_cmd(cmd):
    """运行 adb 命令并返回结果"""
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip()
    except subprocess.CalledProcessError:
        return ""

def get_pid(package):
    pid = run_cmd(f"adb shell pidof {package}")
    return pid if pid else None

def check_main_thread(pid):
    print("\n=== [1] 主线程堆栈 ===")
    output = run_cmd(f"adb shell debuggerd -b {pid}")
    lines = output.splitlines()
    main_stack = []
    capture = False
    for line in lines:
        if "main" in line and "tid" in line:
            capture = True
        if capture:
            if line.strip() == "":
                break
            main_stack.append(line)
    print("\n".join(main_stack))
    if any("dequeueBuffer" in l or "eglSwapBuffers" in l for l in main_stack):
        print("⚠️  主线程卡在 dequeueBuffer / eglSwapBuffers (UI 渲染阻塞)")
        return True
    return False

def check_surfaceflinger():
    print("\n=== [2] SurfaceFlinger BufferQueue 状态 ===")
    output = run_cmd("adb shell dumpsys SurfaceFlinger")
    bq_status = []
    for line in output.splitlines():
        if "BufferQueue" in line or "acquired" in line or "queued" in line or "free" in line:
            bq_status.append(line.strip())
    print("\n".join(bq_status))
    if any("acquired=3" in l and "free=0" in l for l in bq_status):
        print("⚠️  BufferQueue 已满，可能 buffer 未被释放")
        return True
    return False

def check_gfxinfo(package):
    print("\n=== [3] GfxInfo 帧率统计 ===")
    output = run_cmd(f"adb shell dumpsys gfxinfo {package} framestats")
    lines = output.splitlines()[-20:]
    print("\n".join(lines))

def check_logcat():
    print("\n=== [4] 最近 SurfaceFlinger / BufferQueue 日志 ===")
    output = run_cmd("adb logcat -d -s SurfaceFlinger BufferQueueProducer")
    logs = output.splitlines()[-20:]
    print("\n".join(logs))
    if any("dequeueBuffer" in l and "timed out" in l for l in logs):
        print("⚠️  dequeueBuffer 超时，可能是系统层卡死")
        return True
    return False

def main():
    if len(sys.argv) < 2:
        print("用法: python deadlock_checker.py <package_name>")
        sys.exit(1)

    package = sys.argv[1]
    print(f"=== 死锁自动排查工具 ===\nPackage: {package}")

    pid = get_pid(package)
    if not pid:
        print("❌ 未找到进程，请确认包名是否正确，且应用已运行。")
        sys.exit(1)

    print(f"PID: {pid}")

    stuck_ui = check_main_thread(pid)
    bq_full = check_surfaceflinger()
    check_gfxinfo(package)
    stuck_sf = check_logcat()

    print("\n=== [结论] ===")
    if stuck_ui and bq_full:
        print("🔴  应用主线程卡在 dequeueBuffer，BufferQueue 已满 → 很可能是 buffer 未释放导致死锁")
    elif stuck_ui and stuck_sf:
        print("🔴  主线程卡在 dequeueBuffer，且 SurfaceFlinger 报错 → 可能是系统层（SurfaceFlinger / GPU / HWC）阻塞")
    elif stuck_ui:
        print("🟠  主线程阻塞，但未发现明显 BufferQueue 异常 → 建议进一步抓 SurfaceFlinger trace")
    else:
        print("✅ 未检测到明显的 UI 死锁迹象")

if __name__ == "__main__":
    main()
