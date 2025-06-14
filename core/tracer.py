import frida
import sys
import json
import logging
import threading
import queue
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class DeviceInfo:
    id: str
    name: str
    type: str
    is_usb: bool

@dataclass
class TraceMessage:
    """追踪消息的数据类"""
    type: str
    timestamp: str
    logType: str
    message: str
    method: Optional[str] = None
    exception: Optional[str] = None
    exceptionStack: Optional[str] = None
    stackTrace: Optional[str] = None
    customFields: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceMessage':
        """从字典创建TraceMessage实例"""
        # 提取自定义字段
        custom_fields = {}
        standard_fields = {
            'type', 'timestamp', 'logType', 'message', 
            'method', 'exception', 'exceptionStack', 'stackTrace'
        }
        
        for key, value in data.items():
            if key not in standard_fields:
                custom_fields[key] = value

        return cls(
            type=data.get('type', ''),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            logType=data.get('logType', 'info'),
            message=data.get('message', ''),
            method=data.get('method'),
            exception=data.get('exception'),
            exceptionStack=data.get('exceptionStack'),
            stackTrace=data.get('stackTrace'),
            customFields=custom_fields if custom_fields else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'type': self.type,
            'timestamp': self.timestamp,
            'logType': self.logType,
            'message': self.message
        }
        
        if self.method:
            result['method'] = self.method
        if self.exception:
            result['exception'] = self.exception
        if self.exceptionStack:
            result['exceptionStack'] = self.exceptionStack
        if self.stackTrace:
            result['stackTrace'] = self.stackTrace
        if self.customFields:
            result.update(self.customFields)
            
        return result

    def format_message(self) -> str:
        """格式化消息为可读字符串"""
        parts = [
            f"[{self.timestamp}] [{self.logType.upper()}]",
            f"Message: {self.message}"
        ]
        
        if self.method:
            parts.append(f"Method: {self.method}")
        if self.exception:
            parts.append(f"Exception: {self.exception}")
        if self.exceptionStack:
            parts.append(f"Exception Stack:\n{self.exceptionStack}")
        if self.stackTrace:
            parts.append(f"Stack Trace:\n{self.stackTrace}")
        if self.customFields:
            parts.append("Custom Fields:")
            for key, value in self.customFields.items():
                parts.append(f"  {key}: {value}")
                
        return "\n".join(parts)

class FridaTracer:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.device: Optional[frida.core.Device] = None
        self.session: Optional[frida.core.Session] = None
        self.script: Optional[frida.core.Script] = None
        self.message_queue = queue.Queue()
        self.is_running = False
        self.callback: Optional[Callable[[TraceMessage], None]] = None
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('FridaTracer')

    def list_devices(self) -> List[DeviceInfo]:
        """列出所有可用的设备"""
        devices = []
        try:
            for device in frida.enumerate_devices():
                if not device.id or not device.name or not device.type:
                    continue
                
                devices.append(DeviceInfo(
                    id=device.id,
                    name=device.name,
                    type=device.type,
                    is_usb=device.type == 'usb'
                ))
        except frida.ProcessNotFoundError as e:
            self.logger.error(f"Failed to enumerate devices: {e}")
        return devices

    def attach_to_device(self, device_id: str) -> bool:
        """附加到指定设备"""
        try:
            self.device = frida.get_device(device_id)
            self.logger.info(f"Successfully attached to device: {device_id}")
            return True
        except frida.ProcessNotFoundError as e:
            self.logger.error(f"Failed to attach to device {device_id}: {e}")
            return False

    def spawn_application(self, package_name: str) -> bool:
        """启动目标应用"""
        if not self.device:
            self.logger.error("No device attached")
            return False

        try:
            pid = self.device.spawn([package_name])
            self.session = self.device.attach(pid)
            self.device.resume(pid)
            self.logger.info(f"Successfully spawned application: {package_name} (PID: {pid})")
            return True
        except frida.ProcessNotFoundError as e:
            self.logger.error(f"Failed to spawn application {package_name}: {e}")
            return False

    def attach_to_process(self, process_name: str) -> bool:
        """附加到运行中的进程"""
        if not self.device:
            self.logger.error("No device attached")
            return False

        try:
            pid = self.device.get_process(process_name).pid
            self.session = self.device.attach(pid)
            self.logger.info(f"Successfully attached to process: {process_name} (PID: {pid})")
            return True
        except frida.ProcessNotFoundError as e:
            self.logger.error(f"Failed to attach to process {process_name}: {e}")
            return False

    def load_script(self, script_path: str) -> bool:
        """加载Frida脚本"""
        if not self.session:
            self.logger.error("No session available")
            return False

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()

            self.script = self.session.create_script(script_content)
            
            # 设置消息处理
            self.script.on('message', self._on_message)
            
            self.script.load()
            self.logger.info(f"Successfully loaded script: {script_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load script {script_path}: {e}")
            return False

    def start_tracing(self, callback: Optional[Callable[[TraceMessage], None]] = None) -> None:
        """开始追踪
        
        Args:
            callback: 处理TraceMessage的回调函数
        """
        if not self.script:
            self.logger.error("No script loaded")
            return

        self.callback = callback
        self.is_running = True
        
        # 启动消息处理线程
        self.message_thread = threading.Thread(target=self._message_loop)
        self.message_thread.daemon = True
        self.message_thread.start()

        try:
            self.script.post({'type': 'start'})
            self.logger.info("Tracing started")
        except Exception as e:
            self.logger.error(f"Failed to start tracing: {e}")
            self.is_running = False

    def stop_tracing(self) -> None:
        """停止追踪"""
        if not self.script:
            return

        try:
            self.script.post({'type': 'stop'})
            self.is_running = False
            self.logger.info("Tracing stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop tracing: {e}")

    def _on_message(self, message: Dict[str, Any], data: Optional[bytes]) -> None:
        """处理来自脚本的消息"""
        if message['type'] == 'send':
            try:
                payload = message['payload']
                if isinstance(payload, str):
                    # 处理字符串格式的payload
                    payload = json.loads(payload)
                
                if payload.get('type') == 'trace':
                    trace_message = TraceMessage.from_dict(payload)
                    
                    # 特殊处理函数调用数据
                    if trace_message.logType in ['call', 'return'] and trace_message.customFields and 'data' in trace_message.customFields:
                        call_data = trace_message.customFields['data']
                        # 确保调用数据包含所有必要字段
                        if all(k in call_data for k in ['caller', 'callee', 'timestamp']):
                            self.message_queue.put(trace_message)
                        else:
                            self.logger.warning(f"Invalid call data format: {call_data}")
                    else:
                        self.message_queue.put(trace_message)
                else:
                    # 处理其他类型的消息
                    self.message_queue.put(payload)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse message payload: {e}")
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
        elif message['type'] == 'error':
            self.logger.error(f"Script error: {message['description']}")

    def _message_loop(self) -> None:
        """消息处理循环"""
        while self.is_running:
            try:
                message = self.message_queue.get(timeout=1)
                if self.callback:
                    if isinstance(message, TraceMessage):
                        # 处理函数调用消息
                        if message.logType in ['call', 'return'] and message.customFields and 'data' in message.customFields:
                            call_data = message.customFields['data']
                            if call_data.get('type') in ['call', 'return']:
                                self.callback(message)
                            else:
                                self.logger.warning(f"Invalid call type in data: {call_data}")
                        else:
                            # 处理其他类型的消息
                            self.callback(message)
                    else:
                        # 处理旧格式的消息
                        self.logger.warning(f"Received old format message: {message}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in message loop: {e}")
                self.logger.exception(e)

    def cleanup(self) -> None:
        """清理资源"""
        self.stop_tracing()
        if self.script:
            self.script.unload()
        if self.session:
            self.session.detach()
        self.device = None
        self.session = None
        self.script = None
        self.logger.info("Cleanup completed")

    def is_package_installed(self, package_name: str) -> bool:
        """检查指定包是否已安装在设备上"""
        if not self.device:
            self.logger.error("No device attached")
            return False

        try:
            # 使用frida的enumerate_processes来获取所有进程
            processes = self.device.enumerate_processes()
            # 检查包名是否在进程列表中
            for process in processes:
                if process.name == package_name:
                    self.logger.info(f"Package {package_name} is installed")
                    return True
            
            # 如果进程列表中没有找到，尝试使用spawn来验证
            try:
                pid = self.device.spawn([package_name])
                self.device.kill(pid)  # 立即终止spawn的进程
                self.logger.info(f"Package {package_name} is installed (verified via spawn)")
                return True
            except frida.ProcessNotFoundError:
                self.logger.warning(f"Package {package_name} is not installed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking package installation: {e}")
            return False 