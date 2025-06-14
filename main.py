#!/usr/bin/env python3
import os
import sys
import json
import yaml
import logging
import argparse
import time
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, Union

from core.tracer import FridaTracer, TraceMessage
from core.processor import CallGraphProcessor
from core.visualizer import CallGraphVisualizer

def load_config(config_path: Path) -> Dict[str, Any]:
    """加载配置文件"""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        if config_path.suffix == '.yaml':
            return yaml.safe_load(f)
        elif config_path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

def setup_logging(log_level: str = 'INFO') -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    parser = argparse.ArgumentParser(description='Function Call Graph Generator')
    parser.add_argument('--config', '-c', required=True, help='Path to config file')
    parser.add_argument('--device', '-d', help='Device ID to attach to')
    parser.add_argument('--package', '-p', help='Package name to trace')
    parser.add_argument('--output', '-o', default='outputs', help='Output directory')
    parser.add_argument('--log-level', '-l', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                      help='Logging level')
    parser.add_argument('--no-spawn', action='store_true', help='Disable spawn mode and attach to running process')
    args = parser.parse_args()

    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger('main')

    try:
        # 加载配置
        config = load_config(Path(args.config))
        logger.info(f"Loaded config from {args.config}")

        # 初始化追踪器
        tracer = FridaTracer(args.config)
        
        # 列出可用设备
        devices = tracer.list_devices()
        if not devices:
            logger.error("No devices found")
            return 1
        
        logger.info("Available devices:")
        for device in devices:
            logger.info(f"  - {device.name} ({device.id})")
        
        # 选择设备
        device_id = args.device
        if not device_id and len(devices) == 1:
            device_id = devices[0].id
        elif not device_id:
            logger.error("Multiple devices found, please specify one with --device")
            return 1
        
        # 附加到设备
        if not tracer.attach_to_device(device_id):
            logger.error(f"Failed to attach to device: {device_id}")
            return 1
        
        # 选择目标应用
        package_name = args.package
        if not package_name and 'apps' in config:
            if len(config['apps']) == 1:
                package_name = config['apps'][0]['package_name']
            else:
                logger.error("Multiple apps in config, please specify one with --package")
                return 1
        
        if not package_name:
            logger.error("No target package specified")
            return 1
        
        # 检查应用是否已安装
        if not tracer.is_package_installed(package_name):
            logger.error(f"Package {package_name} is not installed on the device")
            return 1

        # 确定启动模式
        should_spawn = not args.no_spawn and config.get('spawn', True)
        
        if should_spawn:
            logger.info(f"Starting {package_name} in spawn mode")
            if not tracer.spawn_application(package_name):
                logger.error(f"Failed to spawn application: {package_name}")
                return 1
        else:
            logger.info(f"Attaching to running {package_name} process")
            if not tracer.attach_to_process(package_name):
                logger.error(f"Failed to attach to process: {package_name}")
                return 1
        
        # 初始化处理器
        processor = CallGraphProcessor(args.output)
        
        # 定义消息回调
        def on_message(message: Union[TraceMessage, Dict[str, Any]]) -> None:
            """处理来自Frida的消息
            
            Args:
                message: TraceMessage对象或字典格式的消息
            """
            if isinstance(message, TraceMessage):
                # 处理新的TraceMessage格式
                if message.logType == 'stack_trace':
                    # 处理堆栈信息
                    processor.process_call_record(message.to_dict())
                else:
                    # 处理其他类型的日志消息
                    logger.debug(message.format_message())
            else:
                # 处理旧格式的消息
                if message.get('type') == 'trace':
                    if message.get('logType') == 'stack_trace':
                        # 处理新的堆栈信息格式
                        processor.process_call_record(message)
                    elif message.get('logType') in ['call', 'return']:
                        # 处理旧的调用记录格式
                        if 'data' in message:
                            processor.process_call_record(message)
                    else:
                        logger.debug(f"Received message: {message}")
                else:
                    logger.debug(f"Received message: {message}")
        
        # 加载并启动脚本
        script_path = Path('agents/_agent.js')
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return 1
        
        if not tracer.load_script(str(script_path)):
            logger.error("Failed to load script")
            return 1
        
        # 开始追踪
        logger.info(f"Starting trace for {package_name} in {'spawn' if should_spawn else 'attach'} mode")
        tracer.start_tracing(callback=on_message)
        
        try:
            # 等待用户中断
            logger.info("Tracing started. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping trace...")
        finally:
            # 停止追踪
            tracer.stop_tracing()
            
            # 生成并保存图
            graph = processor.generate_graph()
            json_file = processor.save_graph(format='json')
            processor.save_graph(format='graphml')
            
            # 生成可视化
            visualizer = CallGraphVisualizer(args.output)
            try:
                # 生成HTML报告
                report_file = visualizer.generate_html_report(json_file)
                # 自动打开报告
                webbrowser.open(f'file://{Path(report_file).absolute()}')
                logger.info(f"Call graph report generated: {report_file}")
            except Exception as e:
                logger.error(f"Failed to generate visualization: {e}")
            
            # # 输出统计信息
            # stats = processor.get_statistics()
            # logger.info("Tracing statistics:")
            # logger.info(f"  Total calls: {stats['total_calls']}")
            # logger.info(f"  Unique functions: {stats['unique_functions']}")
            # logger.info(f"  Unique calls: {stats['unique_calls']}")
            
            # # 输出最常调用的函数
            # logger.info("\nMost called functions:")
            # for func_id, node in stats['most_called_functions']:
            #     logger.info(f"  {func_id}: {node.call_count} calls")
            
            # # 输出耗时最长的函数
            # logger.info("\nLongest duration functions:")
            # for func_id, node in stats['longest_duration_functions']:
            #     logger.info(f"  {func_id}: {node.total_duration:.2f}ms total, {node.avg_duration:.2f}ms avg")
            
            # 清理资源
            tracer.cleanup()
        
        return 0
    
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 