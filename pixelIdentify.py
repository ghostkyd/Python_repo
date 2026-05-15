import cv2
import argparse
from datetime import timedelta
import math
import numpy as np
import sys

def analyze_video_area_color(video_path, threshold=30, sample_rate=1, 
                           center_x=None, center_y=None, block_size=10, show_progress=True):
    """
    分析视频指定区域像素颜色变化
    
    Args:
        video_path: 视频文件路径
        threshold: 颜色变化检测阈值（0-255）
        sample_rate: 采样率，每隔多少帧检测一次
        center_x: 检测区域中心x坐标（默认为画面中心）
        center_y: 检测区域中心y坐标（默认为画面中心）
        block_size: 检测区域大小（正方形边长，默认10像素）
        show_progress: 是否显示进度
    """
    
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"错误：无法打开视频文件 {video_path}")
        return
    
    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 计算检测区域坐标
    if center_x is None:
        center_x = width // 2
    if center_y is None:
        center_y = height // 2
    
    # 确保检测区域在画面范围内
    half_block = block_size // 2
    x1 = max(0, center_x - half_block)
    y1 = max(0, center_y - half_block)
    x2 = min(width, center_x + half_block)
    y2 = min(height, center_y + half_block)
    
    actual_block_size = min(x2 - x1, y2 - y1)
    
    print(f"视频信息:")
    print(f"  分辨率: {width}x{height}")
    print(f"  帧率: {fps:.2f} FPS")
    print(f"  总帧数: {total_frames}")
    print(f"  总时长: {timedelta(seconds=total_frames/fps)}")
    print(f"  检测区域: ({x1}, {y1}) - ({x2}, {y2})")
    print(f"  区域大小: {actual_block_size}x{actual_block_size}")
    print("-" * 60)
    
    # 初始化变量
    first_color = None
    last_color = None
    frame_count = 0
    processed_frames = 0
    last_progress = -1
    
    print("开始分析视频...")
    print("时间戳\t\t颜色变化\t区域中心\t平均RGB值")
    print("-" * 70)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # 显示进度
        if show_progress and total_frames > 0:
            progress = int((frame_count / total_frames) * 100)
            if progress != last_progress and progress % 2 == 0:  # 每2%更新一次
                last_progress = progress
                sys.stdout.write(f"\r处理进度: {progress}% ({frame_count}/{total_frames} 帧)")
                sys.stdout.flush()
        
        # 根据采样率跳过帧以提高性能
        if frame_count % sample_rate != 0:
            continue
            
        processed_frames += 1
        
        # 提取检测区域
        roi = frame[y1:y2, x1:x2]
        
        # 计算区域平均颜色（BGR格式）
        avg_color = np.mean(roi, axis=(0, 1))
        b, g, r = map(int, avg_color)
        current_color = (r, g, b)
        
        # 记录第一帧的颜色作为基准
        if first_color is None:
            first_color = current_color
            last_color = current_color
            timestamp = frame_count / fps
            time_str = str(timedelta(seconds=timestamp))
            if show_progress:
                sys.stdout.write("\n")
            print(f"{time_str[:12]}\t初始颜色\t({center_x}, {center_y})\t{current_color}")
            continue
        
        # 计算颜色差异（欧几里得距离）
        dr = current_color[0] - last_color[0]
        dg = current_color[1] - last_color[1]
        db = current_color[2] - last_color[2]
        color_diff = math.sqrt(dr*dr + dg*dg + db*db)
        
        # 如果颜色变化超过阈值，则记录
        if color_diff > threshold:
            timestamp = frame_count / fps
            time_str = str(timedelta(seconds=timestamp))
            
            # 计算与初始颜色的差异
            dr_init = current_color[0] - first_color[0]
            dg_init = current_color[1] - first_color[1]
            db_init = current_color[2] - first_color[2]
            initial_diff = math.sqrt(dr_init*dr_init + dg_init*dg_init + db_init*db_init)
            
            if show_progress:
                sys.stdout.write("\n")
            print(f"{time_str[:12]}\t{initial_diff:.1f}\t\t({center_x}, {center_y})\t{current_color}")
            last_color = current_color
    
    # 完成进度显示
    if show_progress:
        sys.stdout.write(f"\r处理进度: 100% ({total_frames}/{total_frames} 帧)\n")
        sys.stdout.flush()
    
    # 清理资源
    cap.release()
    
    print("-" * 70)
    print(f"分析完成！处理了 {processed_frames} 帧（总帧数: {frame_count}）")
    
    if first_color is not None:
        print(f"初始颜色: {first_color}")
        print(f"最终颜色: {last_color}")
        
        # 计算总体颜色变化
        dr = last_color[0] - first_color[0]
        dg = last_color[1] - first_color[1]
        db = last_color[2] - first_color[2]
        total_diff = math.sqrt(dr*dr + dg*dg + db*db)
        print(f"总体颜色变化: {total_diff:.1f}")

def main():
    parser = argparse.ArgumentParser(description='分析视频指定区域像素颜色变化')
    parser.add_argument('video_path', help='视频文件路径')
    parser.add_argument('-t', '--threshold', type=int, default=30, 
                       help='颜色变化检测阈值 (默认: 30)')
    parser.add_argument('-s', '--sample-rate', type=int, default=1,
                       help='采样率，每隔多少帧检测一次 (默认: 1)')
    parser.add_argument('-x', '--center-x', type=int, default=None,
                       help='检测区域中心x坐标 (默认: 画面中心)')
    parser.add_argument('-y', '--center-y', type=int, default=None,
                       help='检测区域中心y坐标 (默认: 画面中心)')
    parser.add_argument('-b', '--block-size', type=int, default=10,
                       help='检测区域大小 (默认: 10像素)')
    parser.add_argument('--no-progress', action='store_true',
                       help='不显示进度信息')
    
    args = parser.parse_args()
    
    analyze_video_area_color(
        args.video_path, 
        args.threshold, 
        args.sample_rate,
        args.center_x,
        args.center_y,
        args.block_size,
        not args.no_progress
    )

if __name__ == "__main__":
    main()